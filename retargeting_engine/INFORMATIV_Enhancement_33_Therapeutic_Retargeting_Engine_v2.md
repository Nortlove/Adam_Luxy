# INFORMATIV Enhancement #33: Therapeutic Retargeting Engine
## Bilateral Psychological Intelligence × Clinical Behavior Change Architecture
## Claude Code Deployment Directive — AUTHORITATIVE SOURCE OF TRUTH

**Version**: 2.0 (Fact-Checked + LLM Persuasion Architecture)
**Date**: March 2026
**Priority**: P0 — Core Differentiator
**Estimated Implementation**: 22 person-weeks (11 sessions)
**Dependencies**: #10 (Journey Tracking), #02 (Blackboard), #06 (Gradient Bridge), #14 (Brand Intelligence), #15 (Copy Generation), #27 (Extended Constructs), #28 (WPP Ad Desk / Sequential Persuasion), #32 (Edge-Centric Maximum Power), Claude Embedded Intelligence Architecture
**Dependents**: StackAdapt Integration, LUXY Ride Pilot, All Future Campaign Execution

**v2.0 Changelog**: All 15 research citations independently fact-checked against primary sources. Two factual errors corrected (Belland scaffolding conflation, Bornstein subliminal figure). Five claims recalibrated with publication-bias-adjusted effect sizes. Matz personality-matching cited with full methodological caveats. CLT replication concerns strengthened. New Domain 16 added: LLM-Powered Adaptive Persuasion (Salvi 2024, Bozdag 2025, Matz 2024) introducing multi-turn conversational adaptation and real-time personality inference. All Bayesian priors now carry BOTH published and calibrated effect sizes. System architecture upgraded to exploit Claude as reasoning engine for dynamic argument generation — the single most powerful addition from 2024-2025 research.

---

## PREAMBLE: WHY THIS EXISTS

The retargeting system in `retargeting_strategy.json` reads like conventional martech with psychological labels. It deploys mechanisms by archetype, but the mechanisms are selected by hand, the sequence is linear, and the system cannot learn. It treats retargeting as "show a different ad" when what INFORMATIV actually has — bilateral psychological intelligence at the conversion-edge level — enables something fundamentally different: **a system that diagnoses WHY a specific person did not convert at a mechanistic level, selects the academically-validated intervention most likely to resolve that specific barrier for that specific psychological profile, and learns from the outcome to improve the next intervention.**

This is not martech retargeting. This is the clinical psychology of conversion.

---

## TABLE OF CONTENTS

### SECTION A: RESEARCH FOUNDATION
1. [Theoretical Architecture: 16 Research Domains](#section-a1)
2. [Key Effect Sizes and Boundary Conditions (Fact-Checked v2.0)](#section-a2)
3. [Personality × Mechanism Interaction Matrix](#section-a3)

### SECTION B: SYSTEM ARCHITECTURE
4. [Core Concept: The Diagnostic Retargeting Loop](#section-b1)
5. [Stage Classification Engine (TTM-Derived)](#section-b2)
6. [Rupture Detection and Repair Protocol](#section-b3)
7. [Scaffolded Message Escalation Framework](#section-b4)
8. [Site Psychological Scoring Pipeline](#section-b5)

### SECTION C: PYDANTIC DATA MODELS
9. [Core Enums and Types](#section-c1)
10. [Conversion Barrier Diagnostic Models](#section-c2)
11. [Therapeutic Touch Sequence Models](#section-c3)
12. [Site Psychological Profile Models](#section-c4)
13. [Learning Signal Models](#section-c5)

### SECTION D: NEO4J SCHEMA
14. [Node Types and Constraints](#section-d1)
15. [Relationship Types](#section-d2)
16. [Key Query Templates](#section-d3)

### SECTION E: CORE ENGINES
17. [Conversion Barrier Diagnostic Engine](#section-e1)
18. [Mechanism Selection Engine (Bayesian)](#section-e2)
19. [Therapeutic Sequence Orchestrator](#section-e3)
20. [Site Crawl and Scoring Pipeline](#section-e4)
21. [Narrative Arc Generator](#section-e5)
22. [Claude Argument Generation Engine](#section-e6)

### SECTION F: INTEGRATION LAYER
23. [FastAPI Endpoints](#section-f1)
24. [LangGraph Orchestration Workflow](#section-f2)
25. [Kafka Event Schemas](#section-f3)
26. [Redis Caching Strategy](#section-f4)
27. [Prometheus Metrics](#section-f5)

### SECTION G: CLAUDE CODE SESSION PLAN
28. [Session 33-1: Barrier Diagnostic Models + Neo4j Schema](#session-1)
29. [Session 33-2: Stage Classification Engine](#session-2)
30. [Session 33-3: Mechanism Selection Engine](#session-3)
31. [Session 33-4: Rupture Detection System](#session-4)
32. [Session 33-5: Site Crawl and Psychological Scoring](#session-5)
33. [Session 33-6: Therapeutic Sequence Orchestrator](#session-6)
34. [Session 33-7: Narrative Arc Generator](#session-7)
35. [Session 33-8: Learning Loop and Gradient Bridge](#session-8)
36. [Session 33-9: StackAdapt Campaign Translation Layer](#session-9)
37. [Session 33-10: Claude Argument Generation Engine](#session-10)
38. [Session 33-11: Integration Testing and Validation](#session-11)

### SECTION H: TESTING AND VALIDATION
39. [Psychological Validity Tests](#section-h1)
40. [A/B Testing Infrastructure Integration](#section-h2)
41. [Success Metrics](#section-h3)

---

# SECTION A: RESEARCH FOUNDATION

<a name="section-a1"></a>
## A.1 Theoretical Architecture: 16 Research Domains

This system draws from 16 academic domains outside conventional advertising. Each domain contributes a specific architectural component. The mapping is not metaphorical — each research finding translates to a concrete system behavior. All citations independently fact-checked against primary sources as of March 2026.

### Domain 1: Transtheoretical Model (Prochaska, DiClemente)
**System Component**: Stage Classification Engine
**Key Finding**: Hall & Rossi (2008) meta-analysis of 120 datasets: progress from pre-contemplation to action requires 1.00 SD increase in perceived pros but only 0.56 SD decrease in perceived cons. The "2:1 ratio" — early messaging must emphasize benefits at double the weight of objection handling.
**Critical Warning**: Action-oriented interventions delivered to pre-contemplative users are not merely ineffective — they generate resistance. Krebs et al. (2010), 88 computer-tailored interventions: dynamically re-tailored interventions that iteratively reassess outperform static segmentation.
**Implementation**: `ConversionStageClassifier` continuously reclassifies users from behavioral signals. Stage-mismatched creative is suppressed automatically.

### Domain 2: Therapeutic Alliance Rupture-Repair (Safran, Muran, Eubanks)
**System Component**: Rupture Detection and Repair Protocol
**Key Finding**: Flückiger et al. (2018), 295 studies, N=30,000+: face-to-face alliance-outcome r=.278 (d=.579). A sub-analysis of 23 Internet-based psychotherapy studies within the same meta-analysis found r=.275 — though a dedicated 2024 teletherapy meta-analysis (Aafjes-van Doorn et al.) found the video/phone alliance-outcome association at r=.15, roughly half the face-to-face estimate. Eubanks et al. (2018) rupture-repair meta-analysis (11 studies, N=1,314): successful rupture resolution r=.29 (d=.62). This is nominally larger than baseline alliance (r=.29 vs r=.278), but the difference is trivial with widely overlapping CIs ([.10, .47] vs [.256, .299]). The directional finding matters for architecture: recovery from breakdowns is AT LEAST as valuable as frictionless journeys.
**Critical caveat**: Companion meta-analysis on training therapists in rupture resolution found a NONSIGNIFICANT effect (r=.11, p=.28) — meaning the skill of recognizing and repairing ruptures is hard to teach even to humans, reinforcing the value of automated detection.
**Rupture Types**: Withdrawal (reduced engagement, cart abandonment, ad blindness — most common, hardest to detect) vs. Confrontation (unsubscribes, complaints — easier to detect, less frequent).
**Implementation**: `RuptureDetector` monitors engagement decay signatures. `RepairStrategySelector` matches repair type to rupture type. Withdrawal repairs use changed-mechanism creative; confrontation repairs use transparent acknowledgment.

### Domain 3: Educational Scaffolding (Vygotsky, Wood/Bruner/Ross)
**System Component**: Scaffolded Message Escalation Framework
**Key Finding**: Belland, Walker, Kim & Lefler (2017), 144 studies: computer-based scaffolding g=0.46 (between-subjects: scaffolded vs control students). Scaffolding that both fades AND adds new content produces strongest effects. A separate Bayesian network meta-analysis (Belland, Walker & Kim, 2017, 56 studies) found large pre-post gains for students with learning disabilities (g=3.13), but this is a WITHIN-SUBJECTS metric from a single study (Xin et al., 2017) — not comparable to the between-subjects g=0.46. The takeaway is that scaffolding has its largest INCREMENTAL value for the most confused/uncertain prospects, but the magnitude of that advantage is poorly estimated.
**CALIBRATION NOTE**: Use g=0.46 as the between-subjects Bayesian prior. Do NOT use g=3.13 as it measures a different quantity (pre-post gain, not scaffolded-vs-control difference).
**Six Functions Mapped to Retargeting**:
- Recruitment → Initial awareness (capture attention, build task commitment)
- Reduction in degrees of freedom → Simplify value proposition to essentials
- Direction maintenance → Reminder ads keeping prospect on conversion path
- Marking critical features → Highlight key differentiators
- Frustration control → Address objections, reduce perceived complexity
- Demonstration → Show product in use via testimonials and case studies
**Implementation**: `ScaffoldIntensityController` governs graduated complexity. Early touches deliver simplest value proposition; mid-sequence introduces depth; late-sequence provides detailed comparison. System fades intervention intensity as user demonstrates autonomous engagement.

### Domain 4: Elaboration Likelihood Model + Persuasion Knowledge Model
**System Component**: PKM-Aware Creative Router
**Key Finding**: Eisend & Tarrahi (2022), 148 papers: PK reaches ~50% of persuasion effect explanatory power. PKM activation transforms beneficial features into perceived selling tactics. BUT: covert personalization does not trigger significant PK effects. 2025 meta-analysis (53 experiments): perceived relevance mediates persuasiveness while perceived intrusiveness does NOT.
**Three-Phase Cascade**:
- Phase 1 (touches 1-2): Low elaboration, peripheral processing, PK not activated
- Phase 2 (touches 3-5): Pattern recognition activates PK, hostile central processing
- Phase 3 (touches 6+): Full PK coping responses
**Implementation**: `PersuasionRouteTracker` estimates current ELM state. Phase 2 creative switches from peripheral cues to strong central arguments. Personalization remains covert (behavioral, not explicit identity references).

### Domain 5: Narrative Transportation Theory (Green, Brock, Slater)
**System Component**: Narrative Arc Generator
**Key Finding**: Van Laer et al. (2014), 132 effect sizes: transportation→affective responses r=.57, transportation→reduced critical thoughts r=-.20. 2019 follow-up: effects STRONGER for commercial stories, user-generated content, and individual reception. Narrative evidence more durable over time than statistical evidence.
**Implementation**: `NarrativeArcBuilder` structures retargeting sequence as episodic story. Each touch advances the narrative. Character identification matched to buyer archetype via testimonial selection engine.

### Domain 6: Foot-in-the-Door / Commitment Escalation (Cialdini, Freedman & Fraser)
**System Component**: Micro-Commitment Ladder
**Key Finding**: Meta-analytic FITD effect r=.15-.17 (Dillard et al., 1984). Time delay between requests does NOT diminish effect. BUT: incentivized first requests undermine self-perception. Low self-concept clarity REVERSES effect (Burger & Guadagno, 2003). Classic FITD only works for high-Preference-for-Consistency individuals.
**Ladder**: click/view → poll/quiz → email signup → content download → trial → small purchase → full purchase
**Implementation**: `MicroCommitmentTracker` records commitment level. Each retargeting touch requests the next-smallest commitment appropriate for the user's PFC score.

### Domain 7: Psychological Reactance Theory (Brehm)
**System Component**: Reactance Governor
**Key Finding**: 2025 meta-analysis (28 articles, 146 effect sizes): freedom-threatening language→anger r=.21, anger→reduced persuasion r=-.23. Wicklund's hydraulic principle: second freedom threat before first dissipates = MULTIPLICATIVE compounding. Trait reactance negatively related to Agreeableness and Conscientiousness.
**Critical**: Tucker (2014): users given privacy control nearly 2× more likely to click personalized ads. Trust must be established before aggressive retargeting (Bleier & Eisenbeiss, 2015).
**Implementation**: `ReactanceGovernor` enforces minimum inter-touch intervals, caps total sequence length, monitors CTR decay as reactance proxy. Autonomy-supporting language ("consider," "perhaps") replaces directive language ("should," "must") for high-reactance profiles.

### Domain 8: Self-Determination Theory (Deci, Ryan)
**System Component**: Autonomy Preservation Layer
**Key Finding**: Ng et al. (2012), 184 datasets: autonomy support→intrinsic motivation r=.42. OIT internalization continuum: move consumers from external regulation (discounts/urgency) through identified regulation (recognizing personal value) toward integrated regulation (purchase aligned with self-concept).
**Implementation**: Each retargeting touch provides meaningful rationale, acknowledges perspective, offers choices, and minimizes pressure. Discount-led creative reserved for late-sequence external-regulation users only.

### Domain 9: Temporal Construal Theory (Trope, Liberman)
**System Component**: Construal Level Modulator
**Key Finding**: Soderberg et al. (2015), 267 experiments: d≈0.24-0.48 for distance→abstraction, but Robust Bayesian reanalysis (Maier et al., 2022) found strong evidence for publication bias across ALL 12 model specifications. Schimmack's (2022) z-curve analysis of 200 CLT articles found expected discovery rate of just 14% vs. observed 74% — a 500% inflation ratio. Individual preregistered replications have failed (e.g., McCarthy & Skowronski multi-lab: d=0.10 nonsignificant vs original d=0.41). The CLIMR multi-lab replication (78 labs, 27 countries) received Stage 1 In-Principle Acceptance in January 2023 but results remain unpublished as of March 2026.
**DESPITE THIS**: The construal FIT effect — matching message abstraction to psychological distance — has direct advertising evidence. Dogan & Erdogan (2020): significant congruence effects on purchase intentions (F(1,346)=21.36, p<.001). A field experiment with airline advertising confirmed matching effects on repurchase. The principle is architecturally sound even if the underlying basic-science effects are smaller than published estimates.
**CALIBRATION NOTE**: Use d=0.10 (the preregistered replication estimate) as the prior, NOT d=0.24-0.48 from publication-biased literature. The construal matching principle is directionally correct but the magnitude is modest.
**Implementation**: Early retargeting (temporally distant) uses abstract "why" framing — brand values, aspirational identity. Late retargeting (proximal to purchase) uses concrete "how" framing — features, price, logistics, checkout simplicity.

### Domain 10: Psychological Ownership + Endowment Effect (Peck, Shu)
**System Component**: Ownership Reactivation Engine
**Key Finding**: Peck & Shu (2009): touch increases perceived ownership (mean 3.27 vs 2.84 on 7-point scale), but the VALUATION increase only occurs when touch is pleasant. Unpleasant touch increases ownership but generates negative affect, producing NO net valuation increase. The mechanism is dual-mediated: ownership + affect must both be positive. Digital browsing analog: interacting with well-designed configurators/booking flows creates pleasant-touch-equivalent ownership; frustrating UX creates negative-touch-equivalent (ownership without valuation). Ownership DECAYS over time. Three-email cart abandonment sequences generate $24.9M vs $3.8M from single emails — 6.5× multiplier.
**Three Antecedents**: Control (interacting with configurators — must be PLEASANT interaction), Investing the self (time researching), Coming to intimately know (reading reviews, comparing).
**Implementation**: `OwnershipReactivator` uses time-decay function. Touch 1 (0-2h): "Your [item] is waiting." Touch 2 (24h): "Imagine using your [item] tomorrow." Touch 3 (48-72h): "You spent time designing your perfect configuration." Touch 4 (5-7d): Loss framing — "Don't lose your [item]." System also tracks UX quality signals — if the booking flow had errors/friction, ownership reactivation messaging should NOT assume positive experience.

### Domain 11: Cognitive Dissonance (Festinger)
**System Component**: Dissonance Amplifier (Careful)
**Key Finding**: Kenworthy et al. (2011): mean d=.61 across dissonance paradigms, but artifact-corrected free-choice paradigm d=.26. Hypocrisy paradigm (Stone & Fernandez, 2008): most effective when people publicly advocate then are reminded of past failure. PFC moderates classic dissonance but NOT hypocrisy.
**Critical**: If dissonance is too aversive, consumers reduce it via attitude change ("I don't really want it") — PERMANENTLY reducing conversion probability.
**Implementation**: Create moderate dissonance easily resolved through purchase. Make interest salient ("You were looking at X"), gently amplify gap, remove consonant cognitions for non-purchase, make behavioral resolution frictionless.

### Domain 12: Social Learning / Modeling (Bandura)
**System Component**: Testimonial Selection Engine
**Key Finding**: Stajkovic & Luthans (1998), 114 studies: self-efficacy→performance r=.38. Braaksma et al. (2002): weak learners learn more from coping models; strong learners from mastery models. Multiple models > single models (Bandura & Menlove, 1968).
**Implementation**: `TestimonialMatcher` selects testimonials by matching model sophistication to prospect state. Hesitant prospects get peer-level "I was skeptical but..." narratives. Confident prospects get aspirational mastery stories.

### Domain 13: Dual Process Theory (Kahneman, Evans, Stanovich)
**System Component**: Processing Route Tracker
**Key Finding**: Bornstein (1989), 208 experimental contrasts (from 134 studies): mere exposure overall r=.26. Brief/subliminal presentations show stronger effects at approximately r≈.37-.49 for specific stimulus types (the commonly cited r=.53 appears to be an inflated subcategory figure — use r≈.40 as the best available estimate for subliminal presentations). Peak liking at ~10-35 exposures (Montoya et al., 2017, 268 growth curves from 81 articles), with no mere exposure effect found for auditory stimuli. Familiarity promotes heuristic processing (Garcia-Marques & Mackie, 2001). To engage System 2 mid-sequence, introduce novel elements that disrupt fluency enough to trigger analytical processing.
**Implementation**: Early touches exploit System 1 fluency. Mid-sequence introduces novel claims requiring deliberation. Late-sequence returns to System 1 with simplified CTA after deliberation phase resolves.

### Domain 14: Implementation Intentions (Gollwitzer)
**System Component**: Intention-Action Bridge
**Key Finding**: Gollwitzer & Sheeran (2006), 94 independent tests: implementation intentions produce d=0.65 ABOVE goal intentions. Sheeran, Listrom & Gollwitzer (2024/2025), 642 tests: larger effects with contingent if-then format, high motivation, and rehearsal.
**CRITICAL PUBLICATION BIAS CAVEAT**: Authors themselves acknowledge "substantial" publication bias (Egger's b=1.06). Bias-corrected estimates from related domain-specific meta-analyses suggest the true applied effect drops dramatically — physical activity d=0.14-0.31, sustainable behavior d=0.47 experimental only. The d=0.65 is almost certainly an overestimate for real-world advertising contexts. Use CALIBRATED d=0.25 as the Bayesian prior, not the published d=0.65.
**Despite reduced effect size, this remains one of the HIGHEST-ROI mechanisms** because it targets the specific intention-action gap (Sheeran 2002: 47% of intenders fail to act), and the mechanism is uniquely suited to late-funnel retargeting where the user already wants the product.
**Implementation**: Late-sequence ads embed if-then structures: "When you're ready for your next airport ride, LUXY Ride is one tap away." Action planning addresses failing to get started; coping planning addresses getting derailed. State-oriented individuals (who struggle with hesitation/rumination) benefit most from externally-provided if-then structures.

### Domain 15: Web Atmospherics + Digital Environment Psychology
**System Component**: Site Psychological Scoring Pipeline
**Key Finding**: Fogg Stanford Web Credibility Project: 46.1% of consumers assess credibility primarily from visual design. Tuch et al. (2012): judgments form within 17ms. Eroglu et al. framework: high task-relevant cues vs. low task-relevant cues. Roschk et al. (2017), 66 studies: warm colors→higher arousal, cool colors→higher satisfaction.
**Implementation**: `SitePsychologicalScorer` crawls target domains and scores them on psychological dimensions matching buyer archetypes. Domain whitelists are dynamically generated from bilateral alignment between site psychology and archetype psychology.

### Domain 16: LLM-Powered Adaptive Persuasion (NEW — 2024-2025 Research)
**System Component**: Claude Reasoning Engine for Dynamic Argument Generation
**This is the single most consequential addition from recent research. It fundamentally changes how the system generates persuasive content.**

**Key Findings**:
- **Salvi et al. (2024, Nature Human Behaviour)**: GPT-4 outperforms humans in persuasive debates, with 81.2% higher odds of post-debate agreement when given basic demographic personalization. But critically, persuasiveness derived from generating FACTUAL CLAIMS, not psychological manipulation techniques. When prevented from using facts, persuasive advantage largely disappeared.
- **Bozdag et al. (2025)**: As few as FOUR conversational turns significantly increases LLM persuasive effectiveness. Multi-turn dialogue substantially outperforms single-shot messaging — the retargeting sequence IS a multi-turn dialogue across time.
- **Matz et al. (2024, Scientific Reports)**: ChatGPT-generated personality-matched messages were effective across personality, ideology, and moral foundations (N=1,788). BUT: Hackenburg & Margetts (2024, PNAS) found LLM-personalized messages based on DEMOGRAPHIC attributes produced a NULL RESULT. Deep psychological personalization works; surface personalization does not.
- **Ramani et al. (2024)**: Real-time personality tracking during conversation, generating tailored responses based on latent personality dimensions inferred from ongoing interaction. The system can LEARN the user's psychology from their behavior within the sequence, not just from pre-computed profiles.
- **2025 arXiv computational persuasion survey**: No single psychological persuasion strategy consistently achieves highest success across scenarios — adaptive, context-dependent selection is necessary. This validates the Thompson Sampling architecture.

**Paradigm Shift for INFORMATIV**: The original architecture treats Claude as a scoring/classification engine (annotate reviews, score sites, classify archetypes). The 2024-2025 evidence says Claude should ALSO be the argument generation engine — producing NOVEL factual arguments tailored to the specific barrier, not just selecting from pre-written creative templates. This is INFORMATIV's deepest moat: no competitor has bilateral psychological intelligence + LLM reasoning generating barrier-specific factual arguments in real time.

**Three architectural implications**:
1. **Fact-based argument generation per barrier**: For each diagnosed barrier, Claude generates the specific factual argument most likely to resolve it for this psychological profile. Trust-deficit barrier for a Careful Truster? Claude generates a novel evidence-based comparison using LUXY Ride's actual performance data. Not a template — a reasoned argument.
2. **Multi-touch coherence**: Claude maintains a "conversation memory" across the retargeting sequence — each subsequent touch references and builds upon previous touches, creating the multi-turn dialogue effect that Bozdag (2025) found dramatically increases persuasiveness.
3. **Real-time personality refinement**: Each behavioral response to a touch provides new personality signal. Claude updates the psychological profile within the sequence, enabling late-sequence touches to be personalized based on observed behavior, not just pre-computed archetypes.

**Implementation**: `ClaudeArgumentEngine` generates per-touch creative copy using: (a) the bilateral edge as context, (b) the diagnosed barrier as the target, (c) the archetype's psychological profile as the audience model, (d) the touch history as "conversation memory," and (e) the brand's actual data as the factual foundation. This replaces template-based creative selection for high-value sequences while retaining templates as fallback for latency-constrained contexts.

**CRITICAL CALIBRATION**: Hackenburg & Margetts (2024) null result with demographic targeting reinforces that SURFACE personalization is worthless — only DEEP psychological personalization (which INFORMATIV uniquely provides via bilateral edges) produces effects. This is architectural validation, not a threat.

<a name="section-a2"></a>
## A.2 Key Effect Sizes Reference Table

These effect sizes govern the Bayesian priors in the Mechanism Selection Engine. All are sourced from meta-analyses.

```python
# adam/retargeting/research_priors.py
# Canonical effect size reference — FACT-CHECKED v2.0
# Each entry carries BOTH the published effect size and the calibrated estimate.
# The calibrated estimate accounts for: publication bias, INFORMATIV's 0.62 lab-to-production
# factor, and domain-specific replication evidence.
# Bayesian priors use CALIBRATED values, not published values.

RESEARCH_EFFECT_SIZES = {
    # Stage-matching
    "ttm_stage_matched_intervention": {
        "published_d": 0.46, "calibrated_d": 0.30,
        "source": "Krebs_2010", "k": 88,
        "calibration_note": "Applied 0.62 lab-to-production factor"
    },
    "ttm_pros_increase_required": {
        "d": 1.00, "source": "Hall_Rossi_2008", "k": 120,
        "verified": True, "note": "Confirmed: 120 datasets, 48 behaviors, ~50,000 participants"
    },
    "ttm_cons_decrease_required": {
        "d": 0.56, "source": "Hall_Rossi_2008", "k": 120, "verified": True
    },

    # Alliance and rupture-repair
    "therapeutic_alliance_outcome": {
        "r": 0.278, "d": 0.579, "source": "Fluckiger_2018", "k": 295,
        "verified": True,
        "note": "Face-to-face. Teletherapy-specific: r=.15 (Aafjes-van Doorn 2024), NOT r=.275"
    },
    "rupture_repair_outcome": {
        "r": 0.29, "d": 0.62, "source": "Eubanks_2018", "k": 11,
        "verified": True,
        "note": "N=1,314. Wide CI [.10, .47]. Training therapists in repair: r=.11 nonsignificant."
    },

    # Scaffolding — CORRECTED: two separate papers
    "computer_scaffolding_between_subjects": {
        "g": 0.46, "source": "Belland_Walker_Kim_Lefler_2017", "k": 144,
        "verified": True, "metric": "between-subjects (scaffolded vs control)"
    },
    # REMOVED: "scaffolding_high_deficit" g=3.13 — this is a within-subjects
    # pre-post metric from a SINGLE STUDY (Xin et al. 2017) in a SEPARATE paper
    # (Belland, Walker & Kim 2017 Bayesian network meta-analysis, k=56).
    # Not comparable to the g=0.46. Do not use as a prior.

    # Narrative transportation
    "transportation_affective": {
        "r": 0.57, "source": "VanLaer_2014", "k": 132,
        "verified": True, "note": "76 articles. 2019 follow-up confirmed commercial/UGC moderation."
    },
    "transportation_critical_thought_reduction": {
        "r": -0.20, "source": "VanLaer_2014", "verified": True
    },
    "narrative_behavior_change": {
        "r": 0.23, "source": "Braddock_Dillard_2016", "verified": True
    },

    # Persuasion knowledge
    "pk_explanatory_power_ratio": {
        "ratio": 0.50, "source": "Eisend_Tarrahi_2022", "k": 148,
        "verified": True,
        "note": "PK→evaluations r=-.098, PK→behavior r=-.122 vs ad effectiveness baselines"
    },

    # Reactance
    "freedom_threat_anger": {"r": 0.21, "source": "ReactanceMeta_2025", "k": 28},
    "anger_persuasion_reduction": {"r": -0.23, "source": "ReactanceMeta_2025"},
    "privacy_control_click_multiplier": {
        "ratio": 2.0, "source": "Tucker_2014",
        "verified": True, "note": "JMR published version: 'nearly twice as likely'"
    },

    # SDT
    "autonomy_support_intrinsic_motivation": {
        "r": 0.42, "source": "Ng_2012", "k": 184,
        "verified": True,
        "note": "Specifically health care contexts. Ryan et al. (2023) reviewed 60 SDT meta-analyses confirming core tenets."
    },

    # FITD
    "foot_in_door": {"r": 0.16, "source": "Dillard_1984"},
    "byaf_technique": {
        "published_g": 0.44, "calibrated_g": 0.11,
        "source": "Fillon_Souchet_Pascual_Girandola_2023", "k": 52,
        "note": "g=0.11 for 7 low-bias studies. R-index 9.77%. Effectively null for digital."
    },

    # Implementation intentions — CORRECTED with publication bias
    "implementation_intentions": {
        "published_d": 0.65, "calibrated_d": 0.25,
        "source": "Gollwitzer_Sheeran_2006", "k": 94,
        "note": "Authors acknowledge 'substantial' pub bias (Egger's b=1.06). "
               "Domain-specific: physical activity d=0.14-0.31, sustainable behavior d=0.47. "
               "Use calibrated_d=0.25 for priors.",
        "update_source": "Sheeran_Listrom_Gollwitzer_2024", "update_k": 642
    },

    # Psychological ownership
    "peck_shu_ownership": {
        "mean_diff": 0.43, "source": "Peck_Shu_2009",
        "note": "Touch→ownership (3.27 vs 2.84 on 7-point). "
               "Valuation increase ONLY with pleasant touch. "
               "Unpleasant touch→ownership but NO valuation increase."
    },
    "ikea_effect": {"d": 0.57, "source": "Pelled_2026", "k": 55, "verified": True},
    "cart_abandonment_3email_vs_1": {"multiplier": 6.5, "source": "industry_benchmark"},

    # Mere exposure — CORRECTED subliminal figure
    "mere_exposure_overall": {
        "r": 0.26, "source": "Bornstein_1989", "k": 208,
        "verified": True, "note": "208 contrasts from 134 studies"
    },
    "mere_exposure_subliminal": {
        "r": 0.40, "source": "Bornstein_1989",
        "note": "CORRECTED from r=.53. Best estimate for brief/subliminal: r≈.37-.49. "
               "The commonly cited r=.53 appears inflated or subcategory-specific."
    },
    "mere_exposure_peak_range": {"min": 10, "max": 35, "source": "Montoya_2017"},

    # Cognitive dissonance
    "dissonance_overall": {"d": 0.61, "source": "Kenworthy_2011"},
    "dissonance_artifact_corrected": {"d": 0.26, "source": "Izuma_Murayama_2013"},

    # Personality-matched persuasion — CORRECTED with caveats
    "personality_matched_clicks": {
        "published_lift": 0.40, "calibrated_lift": 0.20,
        "source": "Matz_2017", "N": 3500000,
        "note": "CRITICAL CAVEATS: Only 2 of 5 experimental tests significant. "
               "Study 1 found ZERO click effect (OR=1.0, p=.98). "
               "Eckles, Gordon & Johnson (2018 PNAS) showed Facebook ad optimization "
               "algorithm creates confounds sufficient to explain results as artifacts. "
               "Sharp, Danenberg & Bellman (2018 PNAS) argued 40% success rate barely "
               "exceeds chance. No independent replication exists. "
               "Calibrated lift halves the published estimate."
    },
    "personality_matched_purchases": {
        "published_lift": 0.50, "calibrated_lift": 0.25,
        "source": "Matz_2017",
        "note": "Same caveats as clicks. Use calibrated values for priors."
    },
    "hirsh_agreeableness_match": {"r_diff": 0.25, "source": "Hirsh_2012", "verified": True},
    "matz_2024_llm_personality": {
        "effective": True, "source": "Matz_2024_ScientificReports", "N": 1788,
        "note": "ChatGPT personality-matched messages effective across personality, "
               "ideology, and moral foundations. Validates LLM generation approach."
    },

    # LLM persuasion — NEW
    "llm_persuasion_debate": {
        "or": 1.812, "source": "Salvi_2024_NatureHumanBehaviour",
        "note": "81.2% higher odds of agreement. Effect driven by factual argument quality, "
               "NOT psychological technique selection."
    },
    "llm_multiturn_threshold": {
        "turns": 4, "source": "Bozdag_2025",
        "note": "As few as 4 conversational turns significantly increases effectiveness."
    },
    "llm_demographic_personalization": {
        "effect": "null", "source": "Hackenburg_Margetts_2024_PNAS",
        "note": "Surface demographic personalization produces NO persuasive advantage. "
               "Only deep psychological personalization works."
    },

    # Construal Level Theory — DOWNGRADED
    "construal_level_distance_abstraction": {
        "published_d": 0.36, "calibrated_d": 0.10,
        "source": "Soderberg_2015", "k": 267,
        "note": "SEVERE publication bias. Schimmack (2022): 14% expected discovery rate "
               "vs 74% observed = 500% inflation. Preregistered replication d=0.10. "
               "CLIMR 78-lab results still unpublished as of March 2026."
    },
    "construal_fit_advertising": {
        "significant": True, "source": "Dogan_Erdogan_2020",
        "note": "F(1,346)=21.36, p<.001 for congruence effect on purchase intentions. "
               "The FIT effect survives even if the basic distance-abstraction link is weak."
    },

    # Ad repetition
    "max_attitude_exposures": {"n": 10, "source": "Schmidt_Eisend_2015", "k": 37, "verified": True},
    "affect_decay_rate": {"rate": -0.62, "source": "Schmidt_Eisend_2015", "verified": True},
    "memory_decay_rate": {"rate": -0.32, "source": "Schmidt_Eisend_2015", "verified": True},

    # Self-efficacy
    "self_efficacy_performance": {"r": 0.38, "source": "Stajkovic_Luthans_1998", "k": 114, "verified": True},

    # Web atmospherics
    "visual_design_credibility_pct": {"pct": 0.461, "source": "Fogg_Stanford"},
    "color_arousal_warm": {"r": 0.15, "source": "Roschk_2017", "k": 66},
    "trust_purchase_intention": {"r": 0.434, "source": "Wang_2022"},

    # INFORMATIV calibration
    "lab_to_production_calibration": {"factor": 0.62, "source": "INFORMATIV_internal"},
}
```

<a name="section-a3"></a>
## A.3 Personality × Mechanism Interaction Matrix

This matrix determines which Cialdini mechanism to deploy for each Big Five profile. Sourced from Alkış & Temizel (2015), Oyibo et al. (2017), replicated cross-culturally.

```python
# adam/retargeting/personality_mechanism_matrix.py

PERSONALITY_MECHANISM_SUSCEPTIBILITY = {
    # Format: trait → {mechanism: susceptibility_direction}
    # +1 = susceptible, -1 = resistant, 0 = neutral
    "agreeableness_high": {
        "liking": +1, "authority": +1, "commitment": +1,
        "social_proof": +1, "reciprocity": +1, "scarcity": 0,
    },
    "conscientiousness_high": {
        "commitment": +1, "reciprocity": +1, "liking": -1,
        "authority": 0, "social_proof": 0, "scarcity": 0,
    },
    "openness_low": {
        "authority": +1, "social_proof": +1, "liking": +1,
        "commitment": 0, "reciprocity": 0, "scarcity": 0,
    },
    "neuroticism_high": {
        "social_proof": +1, "scarcity": +1, "authority": 0,
        "liking": 0, "commitment": 0, "reciprocity": 0,
    },
    "extraversion_high": {
        "scarcity": +1, "liking": 0, "social_proof": 0,
        "authority": 0, "commitment": 0, "reciprocity": 0,
    },
    # Reactance trait (from Enhancement #27 extended constructs)
    "reactance_high": {
        "scarcity": -1, "authority": -1, "commitment": -1,
        "narrative": +1, "autonomy_support": +1,
    },
}
```

---

# SECTION B: SYSTEM ARCHITECTURE

<a name="section-b1"></a>
## B.1 Core Concept: The Diagnostic Retargeting Loop

The fundamental architecture is a DIAGNOSTIC LOOP, not a linear sequence. Each non-conversion is treated as a diagnostic signal that updates the barrier hypothesis.

```
┌─────────────────────────────────────────────────────────────────┐
│                  DIAGNOSTIC RETARGETING LOOP                     │
│                                                                  │
│  ┌──────────┐     ┌──────────────┐     ┌──────────────────┐    │
│  │ BILATERAL │     │   BARRIER    │     │    MECHANISM     │    │
│  │   EDGE    │────▶│  DIAGNOSTIC  │────▶│    SELECTION     │    │
│  │  (Input)  │     │   ENGINE     │     │    ENGINE        │    │
│  └──────────┘     └──────────────┘     └────────┬─────────┘    │
│                                                   │              │
│                                                   ▼              │
│  ┌──────────┐     ┌──────────────┐     ┌──────────────────┐    │
│  │ LEARNING │     │   OUTCOME    │     │   THERAPEUTIC    │    │
│  │  SIGNAL  │◀────│   OBSERVER   │◀────│     TOUCH        │    │
│  │ (Output) │     │              │     │   DELIVERY       │    │
│  └────┬─────┘     └──────────────┘     └──────────────────┘    │
│       │                                                          │
│       │  ┌──────────────────────────────────────────────┐       │
│       └─▶│ BAYESIAN PRIOR UPDATE (Gradient Bridge #06)  │       │
│          │ Updates mechanism effectiveness per profile    │       │
│          └──────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

**Key difference from standard retargeting**: Standard retargeting asks "did they convert?" and repeats the same message. This system asks "WHY didn't they convert?" and deploys a DIFFERENT mechanism targeting the specific barrier.

<a name="section-b2"></a>
## B.2 Stage Classification Engine (TTM-Derived)

Six conversion stages, mapped from TTM but adapted for purchase behavior. Behavioral signals — NOT self-report — drive classification.

```python
class ConversionStage(str, Enum):
    """TTM-derived conversion stages with behavioral signal classifiers."""
    
    UNAWARE = "unaware"
    # No brand interaction. Pre-contemplation equivalent.
    # Signal: No pixel fires, no site visits, no ad engagement.
    # Intervention: Consciousness raising only. NO conversion messaging.
    
    CURIOUS = "curious"
    # Initial brand awareness, low engagement.
    # Signal: Ad impression with >2s dwell OR single site visit <30s.
    # Intervention: Discovery-focused, exploratory content.
    
    EVALUATING = "evaluating"
    # Active comparison, information seeking.
    # Signal: Multiple page views, pricing page visit, competitor site visits.
    # Intervention: Evidence, comparison, social proof. Central-route arguments.
    
    INTENDING = "intending"
    # Decision made psychologically, action not taken.
    # Signal: Cart addition, booking start, email signup, return visit >2x.
    # Intervention: Implementation intentions, friction removal, urgency.
    
    STALLED = "stalled"
    # Was INTENDING but failed to act. The intention-behavior gap.
    # Signal: Cart abandonment, booking abandonment, 48h+ since last INTENDING signal.
    # Intervention: Ownership reactivation, loss framing, if-then prompts.
    
    CONVERTED = "converted"
    # Purchase complete.
    # Signal: Conversion pixel fire.
    # Intervention: STOP all retargeting. Switch to retention track.
```

<a name="section-b3"></a>
## B.3 Rupture Detection and Repair Protocol

```python
class RuptureType(str, Enum):
    """Safran & Muran rupture typology adapted for digital."""
    
    WITHDRAWAL = "withdrawal"
    # Movements AWAY: declining engagement, longer inter-visit gaps,
    # reduced email opens, ad blindness (impressions without clicks).
    # Detection: Engagement velocity < 0.3 × rolling average.
    # Repair: Changed-mechanism creative. Do NOT acknowledge withdrawal
    # explicitly (clinical evidence: self-disclosure ineffective for withdrawal).
    
    CONFRONTATION = "confrontation"
    # Movements AGAINST: unsubscribe, negative review, social complaint,
    # explicit feedback.
    # Detection: Explicit negative signal.
    # Repair: Transparent acknowledgment + changed approach. "We hear you."
    
    DECAY = "decay"
    # Gradual disengagement without clear trigger.
    # Detection: Time since last engagement > 2× median for this archetype.
    # Repair: Re-engagement with novel content. Reset narrative arc.
    
    NONE = "none"
    # No rupture detected. Continue current sequence.
```

<a name="section-b4"></a>
## B.4 Scaffolded Message Escalation Framework

Five escalation levels, each with specific psychological function and research backing.

```python
class ScaffoldLevel(int, Enum):
    """Wood/Bruner/Ross scaffolding levels mapped to retargeting."""
    
    RECRUITMENT = 1
    # Function: Capture attention, build task commitment
    # Message type: Brand awareness, identity alignment
    # Construal: Abstract (why)
    # Processing: System 1 (fluency, mere exposure)
    # Research: Mere exposure r=.26 (Bornstein, 1989)
    
    SIMPLIFICATION = 2
    # Function: Reduce value proposition to essentials
    # Message type: Core benefit, single differentiator
    # Construal: Abstract→Concrete transition
    # Processing: System 1→2 bridge (introduce novel claim)
    # Research: Scaffolding g=0.46 (Belland, 2017)
    
    DIRECTION_MAINTENANCE = 3
    # Function: Keep prospect on conversion path
    # Message type: Reminder, narrative continuation, social proof
    # Construal: Concrete (how)
    # Processing: System 2 (central route arguments survive PK)
    # Research: Narrative transportation r=.57 affect (Van Laer, 2014)
    
    FRUSTRATION_CONTROL = 4
    # Function: Address objections, reduce perceived complexity
    # Message type: Objection handling, risk mitigation, guarantee
    # Construal: Concrete (specifics)
    # Processing: System 2 (coping planning)
    # Research: Implementation intentions d=0.65 (Gollwitzer, 2006)
    
    DEMONSTRATION = 5
    # Function: Show product in use via matched testimonial
    # Message type: Vicarious experience, case study
    # Construal: Concrete (vivid scenario)
    # Processing: System 1 (narrative transportation)
    # Research: Narrative→behavior r=.23 (Braddock & Dillard, 2016)
```

<a name="section-b5"></a>
## B.5 Site Psychological Scoring Pipeline

Crawl target domains and score them on psychological dimensions that align with buyer archetypes.

**Input**: Domain URL list (initial: LUXY Ride competitor and partner sites, luxury travel editorial, review platforms, business travel resources)

**Output**: Per-domain psychological profile with 12 dimensions, stored as SitePsychProfile nodes in Neo4j, used for domain whitelist generation per archetype.

**Scoring Dimensions** (extracted via Claude analysis of page content + visual signals):
1. `trust_signaling` — Credential display, verification badges, transparency
2. `emotional_warmth` — Tone warmth, personal language, community signals
3. `rational_density` — Data, comparisons, specifications, evidence
4. `aspirational_level` — Status signaling, luxury positioning, exclusivity
5. `simplicity` — Cognitive load, navigation complexity, information density
6. `urgency_pressure` — Scarcity cues, countdown timers, limited availability
7. `social_proof_density` — Reviews, testimonials, user counts
8. `narrative_richness` — Storytelling, editorial depth, long-form content
9. `autonomy_respect` — Choice architecture, opt-out ease, pressure level
10. `processing_route` — Central (detail-heavy) vs. peripheral (image/emotion-heavy)
11. `regulatory_framing` — Gain/promotion vs. loss/prevention dominant
12. `construal_level` — Abstract (brand values) vs. concrete (product specs)

---

# SECTION C: PYDANTIC DATA MODELS

<a name="section-c1"></a>
## C.1 Core Enums and Types

```python
# adam/retargeting/models/enums.py

from enum import Enum
from typing import Optional


class ConversionStage(str, Enum):
    UNAWARE = "unaware"
    CURIOUS = "curious"
    EVALUATING = "evaluating"
    INTENDING = "intending"
    STALLED = "stalled"
    CONVERTED = "converted"


class RuptureType(str, Enum):
    WITHDRAWAL = "withdrawal"
    CONFRONTATION = "confrontation"
    DECAY = "decay"
    NONE = "none"


class ScaffoldLevel(int, Enum):
    RECRUITMENT = 1
    SIMPLIFICATION = 2
    DIRECTION_MAINTENANCE = 3
    FRUSTRATION_CONTROL = 4
    DEMONSTRATION = 5


class BarrierCategory(str, Enum):
    """Top-level barrier categories derived from bilateral alignment gaps."""
    TRUST_DEFICIT = "trust_deficit"
    # brand_trust_fit below threshold
    
    REGULATORY_MISMATCH = "regulatory_mismatch"
    # regulatory_fit_score below threshold (wrong gain/loss framing)
    
    PROCESSING_OVERLOAD = "processing_overload"
    # processing_route_match below threshold (messaging too complex)
    
    EMOTIONAL_DISCONNECT = "emotional_disconnect"
    # emotional_resonance below threshold (messaging felt transactional)
    
    PRICE_FRICTION = "price_friction"
    # anchor_susceptibility_match + spending_pain_match below threshold
    
    MOTIVE_MISMATCH = "motive_mismatch"
    # evolutionary_motive_match below threshold (wrong need addressed)
    
    NEGATIVITY_BLOCK = "negativity_block"
    # negativity_bias_match above threshold (negative info weight too high)
    
    REACTANCE_TRIGGERED = "reactance_triggered"
    # persuasion_reactance_match above threshold (felt pushed)
    
    IDENTITY_MISALIGNMENT = "identity_misalignment"
    # personality_brand_alignment below threshold
    
    INTENTION_ACTION_GAP = "intention_action_gap"
    # All alignment scores adequate but no conversion (Gollwitzer gap)


class TherapeuticMechanism(str, Enum):
    """Mechanisms available for barrier resolution. Each maps to research domain."""
    EVIDENCE_PROOF = "evidence_proof"                    # Domain 3: Scaffolding
    NARRATIVE_TRANSPORTATION = "narrative_transportation"  # Domain 5
    SOCIAL_PROOF_MATCHED = "social_proof_matched"         # Domain 12: Bandura
    AUTONOMY_RESTORATION = "autonomy_restoration"         # Domain 8: SDT
    CONSTRUAL_SHIFT = "construal_shift"                   # Domain 9: CLT
    OWNERSHIP_REACTIVATION = "ownership_reactivation"     # Domain 10: Endowment
    IMPLEMENTATION_INTENTION = "implementation_intention"  # Domain 14: Gollwitzer
    MICRO_COMMITMENT = "micro_commitment"                 # Domain 6: FITD
    DISSONANCE_ACTIVATION = "dissonance_activation"       # Domain 11: Festinger
    LOSS_FRAMING = "loss_framing"                         # Domain 10: Loss aversion
    ANXIETY_RESOLUTION = "anxiety_resolution"             # Domain 2: Rupture repair
    FRUSTRATION_CONTROL = "frustration_control"           # Domain 3: Scaffolding
    NOVELTY_DISRUPTION = "novelty_disruption"             # Domain 13: Dual process
    VIVID_SCENARIO = "vivid_scenario"                     # Domain 5: Transportation
    PRICE_ANCHOR = "price_anchor"                         # Domain 9: CLT concrete
    CLAUDE_ARGUMENT = "claude_argument"                   # Domain 16: LLM-generated factual argument
    # CLAUDE_ARGUMENT is the most powerful mechanism. Unlike all others which select
    # from pre-existing creative templates, this generates a NOVEL factual argument
    # tailored to the specific barrier × personality × touch history. It exploits
    # the Salvi (2024) finding that LLM persuasion derives from factual argument
    # quality, and the Bozdag (2025) finding that multi-turn coherence amplifies
    # effectiveness. Available for all barrier types as a high-confidence option
    # when latency budget permits (requires Claude API call, ~500ms).
```

<a name="section-c2"></a>
## C.2 Conversion Barrier Diagnostic Models

```python
# adam/retargeting/models/diagnostics.py

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from uuid import uuid4


class AlignmentGap(BaseModel):
    """A specific bilateral alignment dimension that fell below threshold."""
    dimension: str = Field(description="Name of the bilateral alignment dimension")
    actual_value: float = Field(description="Observed alignment score")
    threshold_value: float = Field(description="Minimum score for conversion")
    gap_magnitude: float = Field(description="threshold - actual (positive = deficit)")
    effect_size_d: float = Field(description="Cohen's d of gap relative to converters")
    rank_in_archetype: int = Field(description="Rank of this gap's importance for this archetype")


class ConversionBarrierDiagnosis(BaseModel):
    """
    Complete diagnostic output for a non-conversion event.
    
    This is the core analytical unit of the Therapeutic Retargeting Engine.
    It answers: WHY did this specific person not convert, given their
    specific psychological profile and the specific brand positioning
    they encountered?
    """
    diagnosis_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    brand_id: str
    archetype_id: str
    diagnosed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Current stage assessment
    conversion_stage: ConversionStage
    stage_confidence: float = Field(ge=0.0, le=1.0)
    stage_signals: Dict[str, float] = Field(
        default_factory=dict,
        description="Behavioral signals that determined stage classification"
    )
    
    # Rupture assessment
    rupture_type: RuptureType
    rupture_severity: float = Field(
        ge=0.0, le=1.0,
        description="0=no rupture, 1=complete disengagement"
    )
    
    # Primary barrier (the MOST important reason for non-conversion)
    primary_barrier: BarrierCategory
    primary_barrier_confidence: float = Field(ge=0.0, le=1.0)
    primary_alignment_gaps: List[AlignmentGap] = Field(
        description="Specific alignment dimensions contributing to primary barrier"
    )
    
    # Secondary barriers (may contribute but are not primary)
    secondary_barriers: List[Tuple[BarrierCategory, float]] = Field(
        default_factory=list,
        description="(barrier_category, confidence) pairs"
    )
    
    # Reactance state
    estimated_reactance_level: float = Field(
        ge=0.0, le=1.0,
        description="Current estimated reactance from prior retargeting touches"
    )
    reactance_budget_remaining: float = Field(
        ge=0.0, le=1.0,
        description="How much more retargeting pressure this user can tolerate"
    )
    
    # PKM state
    persuasion_knowledge_phase: int = Field(
        ge=1, le=3,
        description="1=peripheral, 2=PK activated, 3=full coping"
    )
    
    # Psychological ownership state
    ownership_level: float = Field(
        ge=0.0, le=1.0,
        description="Estimated psychological ownership from browsing behavior"
    )
    ownership_decay_rate: float = Field(
        description="Hours since peak ownership × decay coefficient"
    )
    
    # Touch history
    total_touches_received: int
    touches_since_last_engagement: int
    last_mechanism_deployed: Optional[TherapeuticMechanism]
    last_mechanism_outcome: Optional[str]  # "engaged", "ignored", "bounced"
    
    # Recommended intervention
    recommended_mechanism: TherapeuticMechanism
    recommended_scaffold_level: ScaffoldLevel
    mechanism_confidence: float = Field(ge=0.0, le=1.0)
    mechanism_rationale: str = Field(
        description="Human-readable explanation of why this mechanism was selected"
    )


class BarrierResolutionOutcome(BaseModel):
    """Outcome observation after a therapeutic touch is delivered."""
    outcome_id: str = Field(default_factory=lambda: str(uuid4()))
    diagnosis_id: str = Field(description="Links to the diagnosis this touch attempted to resolve")
    touch_id: str
    user_id: str
    
    # What was deployed
    mechanism_deployed: TherapeuticMechanism
    scaffold_level: ScaffoldLevel
    creative_variant_id: str
    
    # What happened
    impression_delivered: bool
    engagement_type: Optional[str]  # "click", "dwell>5s", "site_visit", "booking_start", None
    converted: bool
    
    # Barrier status after touch
    barrier_resolved: Optional[bool] = Field(
        description="Did the specific barrier targeted get resolved? None if unknown."
    )
    new_barrier_emerged: Optional[BarrierCategory] = Field(
        description="If a new barrier surfaced, what is it?"
    )
    
    # Stage movement
    stage_before: ConversionStage
    stage_after: ConversionStage
    stage_advanced: bool = Field(
        description="Did the user move to a more advanced conversion stage?"
    )
    
    # Timing
    delivered_at: datetime
    observed_at: datetime
    observation_window_hours: int = Field(
        default=48,
        description="How long after delivery we waited before observing outcome"
    )
```

<a name="section-c3"></a>
## C.3 Therapeutic Touch Sequence Models

```python
# adam/retargeting/models/sequences.py

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from uuid import uuid4


class TherapeuticTouch(BaseModel):
    """
    A single retargeting touch — the atomic unit of the therapeutic sequence.
    
    Unlike standard retargeting where each touch is an independent ad impression,
    a therapeutic touch is a DIAGNOSTIC INTERVENTION: it has a specific hypothesis
    about what barrier to resolve, a specific mechanism chosen to resolve it,
    and a specific outcome it expects to observe.
    """
    touch_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence_id: str
    position_in_sequence: int
    
    # Diagnostic context
    diagnosis_id: str = Field(description="The barrier diagnosis this touch responds to")
    target_barrier: BarrierCategory
    target_alignment_dimension: str = Field(
        description="The specific bilateral alignment dimension being addressed"
    )
    
    # Intervention selection
    mechanism: TherapeuticMechanism
    scaffold_level: ScaffoldLevel
    construal_level: str = Field(description="'abstract' or 'concrete'")
    processing_route: str = Field(description="'central' or 'peripheral'")
    
    # Narrative arc position
    narrative_chapter: int = Field(
        ge=1, le=5,
        description="Position in the 5-chapter narrative arc"
    )
    narrative_function: str = Field(
        description="E.g., 'introduce_character', 'present_conflict', 'show_resolution'"
    )
    
    # Creative specification
    creative_strategy: Dict = Field(
        description="Complete creative spec for personality-matched copy generation"
    )
    testimonial_model_type: Optional[str] = Field(
        default=None,
        description="'coping' or 'mastery' per Bandura/Braaksma matching rules"
    )
    
    # Delivery constraints
    min_hours_after_previous: int = Field(
        default=24,
        description="Minimum hours after previous touch (reactance management)"
    )
    max_hours_after_previous: int = Field(
        default=72,
        description="Maximum hours before ownership decay makes touch less effective"
    )
    
    # Trigger conditions
    trigger_type: str = Field(
        description="'time_elapsed', 'site_revisit', 'cart_abandon', 'competitor_visit'"
    )
    trigger_conditions: Dict = Field(
        default_factory=dict,
        description="Specific conditions that must be met to fire this touch"
    )
    
    # Expected outcome
    expected_stage_movement: Optional[ConversionStage]
    expected_engagement_probability: float = Field(ge=0.0, le=1.0)
    
    # Autonomy preservation
    autonomy_language: bool = Field(
        default=True,
        description="Use autonomy-supporting language ('consider', 'perhaps')"
    )
    opt_out_visible: bool = Field(
        default=True,
        description="Show easy opt-out to reduce reactance"
    )


class TherapeuticSequence(BaseModel):
    """
    A complete retargeting sequence for one user × one brand × one archetype.
    
    The sequence is NOT pre-planned linearly. It is a DECISION TREE where
    each subsequent touch is selected based on the outcome of the previous
    touch and the updated barrier diagnosis.
    """
    sequence_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    brand_id: str
    archetype_id: str
    
    # Configuration
    max_touches: int = Field(
        default=7,
        description="Maximum touches before suppression (inverted-U research)"
    )
    max_duration_days: int = Field(
        default=21,
        description="Maximum calendar days for sequence"
    )
    
    # Current state
    touches_delivered: List[TherapeuticTouch] = Field(default_factory=list)
    outcomes_observed: List[BarrierResolutionOutcome] = Field(default_factory=list)
    current_diagnosis: Optional[ConversionBarrierDiagnosis] = None
    
    # Reactance management
    cumulative_reactance: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Accumulated reactance. Wicklund hydraulic model."
    )
    reactance_decay_rate: float = Field(
        default=0.15,
        description="Reactance decay per 24h of no-contact"
    )
    
    # Sequence status
    status: str = Field(
        default="active",
        description="'active', 'paused', 'suppressed', 'converted', 'exhausted'"
    )
    
    # Suppression rules
    suppress_if_ctr_below: float = Field(
        default=0.0003,
        description="If CTR drops below 0.03% at any point, pause 72h"
    )
    suppress_after_max_touches: bool = Field(default=True)
    suppression_duration_days: int = Field(
        default=14,
        description="Days of suppression before re-engagement attempt"
    )
    
    # Narrative arc tracking
    narrative_arc_position: int = Field(
        default=0,
        description="Current position in the 5-chapter narrative arc"
    )
    narrative_arc_type: str = Field(
        default="resolution",
        description="'resolution', 'discovery', 'transformation' — archetype-matched"
    )
    
    # Learning outputs
    mechanism_effectiveness_log: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="mechanism_name → [outcome_scores] for Bayesian updating"
    )
    
    # Cross-archetype reclassification
    reclassification_signals: List[Dict] = Field(
        default_factory=list,
        description="Behavioral signals suggesting archetype reclassification"
    )
    reclassified: bool = Field(default=False)
    original_archetype_id: Optional[str] = None


class SequenceDecisionNode(BaseModel):
    """
    A decision point in the therapeutic sequence tree.
    
    After each touch outcome, the system evaluates which branch to take.
    This is NOT a linear sequence — it's a decision tree.
    """
    node_id: str = Field(default_factory=lambda: str(uuid4()))
    after_touch_position: int
    
    # Evaluation criteria
    if_barrier_resolved: Optional[TherapeuticMechanism] = Field(
        default=None,
        description="Next mechanism if the target barrier was resolved"
    )
    if_barrier_persists: Optional[TherapeuticMechanism] = Field(
        default=None,
        description="Next mechanism if the target barrier was NOT resolved"
    )
    if_new_barrier_emerged: Optional[TherapeuticMechanism] = Field(
        default=None,
        description="Next mechanism if a NEW barrier surfaced"
    )
    if_rupture_detected: Optional[str] = Field(
        default="pause_72h",
        description="Action if engagement rupture detected"
    )
    if_reactance_exceeded: str = Field(
        default="suppress",
        description="Action if cumulative reactance exceeds budget"
    )
    if_stage_advanced: Optional[TherapeuticMechanism] = Field(
        default=None,
        description="Next mechanism if user advanced to next stage"
    )
```

<a name="section-c4"></a>
## C.4 Site Psychological Profile Models

```python
# adam/retargeting/models/site_profiles.py

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


class SitePsychologicalProfile(BaseModel):
    """
    Psychological profile of a website/domain.
    
    Used to match placement environments to buyer archetype psychology.
    A Status Seeker should see ads on sites with high aspirational_level
    and low urgency_pressure. A Careful Truster should see ads on sites
    with high rational_density and high trust_signaling.
    """
    domain: str = Field(description="e.g., 'businesstraveller.com'")
    url_analyzed: str = Field(description="Specific page URL that was crawled")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 12 psychological dimensions (0.0 to 1.0)
    trust_signaling: float = Field(ge=0.0, le=1.0)
    emotional_warmth: float = Field(ge=0.0, le=1.0)
    rational_density: float = Field(ge=0.0, le=1.0)
    aspirational_level: float = Field(ge=0.0, le=1.0)
    simplicity: float = Field(ge=0.0, le=1.0)
    urgency_pressure: float = Field(ge=0.0, le=1.0)
    social_proof_density: float = Field(ge=0.0, le=1.0)
    narrative_richness: float = Field(ge=0.0, le=1.0)
    autonomy_respect: float = Field(ge=0.0, le=1.0)
    processing_route: float = Field(
        ge=0.0, le=1.0,
        description="0=peripheral (image/emotion), 1=central (data/argument)"
    )
    regulatory_framing: float = Field(
        ge=0.0, le=1.0,
        description="0=prevention/loss, 1=promotion/gain"
    )
    construal_level: float = Field(
        ge=0.0, le=1.0,
        description="0=concrete (specs), 1=abstract (values)"
    )
    
    # Metadata
    page_category: str = Field(description="'editorial', 'review', 'ecommerce', 'social', 'news'")
    content_quality_score: float = Field(ge=0.0, le=1.0)
    estimated_audience_affluence: float = Field(ge=0.0, le=1.0)
    
    # Archetype alignment scores (computed from dimension × archetype weight matrix)
    archetype_alignments: Dict[str, float] = Field(
        default_factory=dict,
        description="archetype_id → alignment_score"
    )


class SiteArchetypeAlignment(BaseModel):
    """Pre-computed alignment between a site profile and a buyer archetype."""
    domain: str
    archetype_id: str
    alignment_score: float = Field(ge=0.0, le=1.0)
    
    # Which dimensions drove the alignment
    dimension_contributions: Dict[str, float] = Field(
        description="dimension_name → contribution to alignment score"
    )
    
    # Recommendation
    include_in_whitelist: bool
    whitelist_confidence: float = Field(ge=0.0, le=1.0)
```

<a name="section-c5"></a>
## C.5 Learning Signal Models

```python
# adam/retargeting/models/learning.py

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


class MechanismEffectivenessSignal(BaseModel):
    """
    Learning signal sent to the Gradient Bridge (#06) after each touch outcome.
    
    This is how the system learns which mechanisms work for which
    psychological profiles. Each signal updates the Bayesian posterior
    for mechanism effectiveness conditioned on personality dimensions.
    """
    signal_id: str
    sequence_id: str
    touch_id: str
    
    # Context
    archetype_id: str
    user_personality_vector: List[float] = Field(
        description="65-dimensional buyer psychology vector"
    )
    barrier_category: BarrierCategory
    alignment_dimension_targeted: str
    
    # Intervention
    mechanism_deployed: TherapeuticMechanism
    scaffold_level: ScaffoldLevel
    construal_level: str
    narrative_chapter: int
    
    # Outcome
    engagement_occurred: bool
    stage_advanced: bool
    converted: bool
    barrier_resolved: Optional[bool]
    
    # Composite outcome score (for Thompson Sampling update)
    outcome_score: float = Field(
        ge=0.0, le=1.0,
        description="Weighted composite: 0.1×engagement + 0.3×stage_advance + 0.6×conversion"
    )
    
    # Reactance observation
    reactance_indicator: float = Field(
        ge=-1.0, le=1.0,
        description="Negative = engagement increased, Positive = engagement decreased"
    )
    
    # Timestamp
    observed_at: datetime


class SequenceLearningReport(BaseModel):
    """
    Comprehensive learning report generated when a sequence completes.
    
    Fed back to the Bayesian prior hierarchy for cross-user,
    cross-archetype, and cross-brand learning.
    """
    sequence_id: str
    user_id: str
    brand_id: str
    archetype_id: str
    
    # Sequence outcome
    final_status: str  # "converted", "suppressed", "exhausted"
    total_touches: int
    total_days: int
    converted: bool
    
    # Per-touch mechanism effectiveness
    mechanism_outcomes: List[MechanismEffectivenessSignal]
    
    # Barrier resolution chain
    barriers_diagnosed: List[BarrierCategory]
    barriers_resolved: List[BarrierCategory]
    barriers_unresolved: List[BarrierCategory]
    
    # Stage progression
    stage_trajectory: List[ConversionStage]
    
    # Reactance trajectory
    reactance_trajectory: List[float]
    peak_reactance: float
    
    # Cross-archetype signal
    reclassification_occurred: bool
    reclassified_to: Optional[str]
    
    # Key learnings (human-readable for dashboard)
    key_insight: str = Field(
        description="E.g., 'Trust-deficit barriers for high-agreeableness users resolve "
                    "2.3× faster with evidence_proof than with social_proof_matched'"
    )
```

---

# SECTION D: NEO4J SCHEMA

<a name="section-d1"></a>
## D.1 Node Types and Constraints

```cypher
// ============================================================
// INFORMATIV Enhancement #33: Therapeutic Retargeting Engine
// Neo4j Schema Definition
// ============================================================

// --- Conversion Barrier Diagnosis Node ---
CREATE CONSTRAINT barrier_diagnosis_id IF NOT EXISTS
FOR (bd:BarrierDiagnosis) REQUIRE bd.diagnosis_id IS UNIQUE;

// Properties: diagnosis_id, user_id, brand_id, archetype_id,
//   diagnosed_at, conversion_stage, stage_confidence,
//   primary_barrier, primary_barrier_confidence,
//   rupture_type, rupture_severity,
//   estimated_reactance_level, reactance_budget_remaining,
//   persuasion_knowledge_phase, ownership_level,
//   recommended_mechanism, mechanism_confidence

// --- Therapeutic Touch Node ---
CREATE CONSTRAINT therapeutic_touch_id IF NOT EXISTS
FOR (tt:TherapeuticTouch) REQUIRE tt.touch_id IS UNIQUE;

// Properties: touch_id, sequence_id, position_in_sequence,
//   mechanism, scaffold_level, construal_level, processing_route,
//   narrative_chapter, narrative_function,
//   trigger_type, delivered_at,
//   autonomy_language, opt_out_visible

// --- Therapeutic Sequence Node ---
CREATE CONSTRAINT therapeutic_sequence_id IF NOT EXISTS
FOR (ts:TherapeuticSequence) REQUIRE ts.sequence_id IS UNIQUE;

// Properties: sequence_id, user_id, brand_id, archetype_id,
//   max_touches, max_duration_days, status,
//   cumulative_reactance, narrative_arc_type,
//   started_at, completed_at, final_status

// --- Site Psychological Profile Node ---
CREATE CONSTRAINT site_profile_domain IF NOT EXISTS
FOR (sp:SitePsychProfile) REQUIRE sp.domain IS UNIQUE;

// Properties: domain, url_analyzed, analyzed_at,
//   trust_signaling, emotional_warmth, rational_density,
//   aspirational_level, simplicity, urgency_pressure,
//   social_proof_density, narrative_richness, autonomy_respect,
//   processing_route, regulatory_framing, construal_level,
//   page_category, content_quality_score

// --- Mechanism Effectiveness Prior Node ---
// (Extends existing BayesianPrior pattern from #32)
CREATE CONSTRAINT mechanism_prior_id IF NOT EXISTS
FOR (mp:MechanismPrior) REQUIRE mp.prior_id IS UNIQUE;

// Properties: prior_id, mechanism, barrier_category,
//   archetype_id, alpha, beta (Thompson Sampling),
//   sample_count, last_updated,
//   personality_interaction_weights (vector)

// --- Indexes for query performance ---
CREATE INDEX barrier_diagnosis_user IF NOT EXISTS
FOR (bd:BarrierDiagnosis) ON (bd.user_id);

CREATE INDEX barrier_diagnosis_archetype IF NOT EXISTS
FOR (bd:BarrierDiagnosis) ON (bd.archetype_id);

CREATE INDEX therapeutic_touch_sequence IF NOT EXISTS
FOR (tt:TherapeuticTouch) ON (tt.sequence_id);

CREATE INDEX therapeutic_sequence_status IF NOT EXISTS
FOR (ts:TherapeuticSequence) ON (ts.status);

CREATE INDEX site_profile_category IF NOT EXISTS
FOR (sp:SitePsychProfile) ON (sp.page_category);

CREATE INDEX mechanism_prior_lookup IF NOT EXISTS
FOR (mp:MechanismPrior) ON (mp.mechanism, mp.barrier_category, mp.archetype_id);
```

<a name="section-d2"></a>
## D.2 Relationship Types

```cypher
// --- Diagnostic relationships ---

// Diagnosis is based on a bilateral edge
(bd:BarrierDiagnosis)-[:DIAGNOSED_FROM]->(ce:ConversionEdge)

// Diagnosis targets specific alignment gap
(bd:BarrierDiagnosis)-[:TARGETS_GAP {dimension: str, gap_magnitude: float}]->(bp:BayesianPrior)

// --- Sequence relationships ---

// Sequence belongs to user × brand
(ts:TherapeuticSequence)-[:FOR_USER]->(u:User)
(ts:TherapeuticSequence)-[:FOR_BRAND]->(b:Brand)
(ts:TherapeuticSequence)-[:FOR_ARCHETYPE]->(ca:CustomerArchetype)

// Touch belongs to sequence
(tt:TherapeuticTouch)-[:PART_OF]->(ts:TherapeuticSequence)

// Touch responds to diagnosis
(tt:TherapeuticTouch)-[:RESPONDS_TO]->(bd:BarrierDiagnosis)

// Touch produces outcome
(tt:TherapeuticTouch)-[:PRODUCED]->(bro:BarrierResolutionOutcome)

// Outcome updates diagnosis
(bro:BarrierResolutionOutcome)-[:UPDATED_DIAGNOSIS]->(bd:BarrierDiagnosis)

// --- Site relationships ---

// Site aligns with archetype
(sp:SitePsychProfile)-[:ALIGNS_WITH {score: float}]->(ca:CustomerArchetype)

// Touch served on site
(tt:TherapeuticTouch)-[:SERVED_ON]->(sp:SitePsychProfile)

// --- Learning relationships ---

// Outcome generates learning signal
(bro:BarrierResolutionOutcome)-[:GENERATES_SIGNAL]->(mes:MechanismEffectivenessSignal)

// Signal updates mechanism prior
(mes:MechanismEffectivenessSignal)-[:UPDATES]->(mp:MechanismPrior)
```

<a name="section-d3"></a>
## D.3 Key Query Templates

```python
# adam/retargeting/queries.py

QUERIES = {
    "get_active_sequences_for_user": """
        MATCH (ts:TherapeuticSequence {user_id: $user_id, status: 'active'})
        OPTIONAL MATCH (ts)<-[:PART_OF]-(tt:TherapeuticTouch)
        WITH ts, collect(tt) AS touches
        RETURN ts, touches
        ORDER BY ts.started_at DESC
    """,
    
    "get_mechanism_prior": """
        MATCH (mp:MechanismPrior {
            mechanism: $mechanism,
            barrier_category: $barrier_category,
            archetype_id: $archetype_id
        })
        RETURN mp.alpha, mp.beta, mp.sample_count, mp.last_updated
    """,
    
    "update_mechanism_prior_thompson": """
        MATCH (mp:MechanismPrior {prior_id: $prior_id})
        SET mp.alpha = mp.alpha + $success_count,
            mp.beta = mp.beta + $failure_count,
            mp.sample_count = mp.sample_count + $total_count,
            mp.last_updated = datetime()
        RETURN mp
    """,
    
    "get_site_whitelist_for_archetype": """
        MATCH (sp:SitePsychProfile)-[a:ALIGNS_WITH]->(ca:CustomerArchetype {archetype_id: $archetype_id})
        WHERE a.score >= $min_alignment_score
        RETURN sp.domain, a.score
        ORDER BY a.score DESC
        LIMIT $max_domains
    """,
    
    "get_barrier_resolution_rate": """
        MATCH (tt:TherapeuticTouch {mechanism: $mechanism})-[:PRODUCED]->(bro:BarrierResolutionOutcome)
        MATCH (tt)-[:RESPONDS_TO]->(bd:BarrierDiagnosis {primary_barrier: $barrier_category})
        MATCH (bd)<-[:FOR_ARCHETYPE]-(ca:CustomerArchetype {archetype_id: $archetype_id})
        WITH count(bro) AS total,
             sum(CASE WHEN bro.barrier_resolved = true THEN 1 ELSE 0 END) AS resolved
        RETURN total, resolved, toFloat(resolved) / total AS resolution_rate
    """,
    
    "learning_query_mechanism_personality_interaction": """
        MATCH (mes:MechanismEffectivenessSignal {mechanism_deployed: $mechanism})
        WITH mes, mes.user_personality_vector AS pv
        WHERE mes.outcome_score > 0
        RETURN avg(pv[0]) AS avg_openness_success,
               avg(pv[1]) AS avg_conscientiousness_success,
               avg(pv[2]) AS avg_extraversion_success,
               avg(pv[3]) AS avg_agreeableness_success,
               avg(pv[4]) AS avg_neuroticism_success,
               count(*) AS n_successes
    """,
}
```

---

# SECTION E: CORE ENGINES

<a name="section-e1"></a>
## E.1 Conversion Barrier Diagnostic Engine

```python
# adam/retargeting/engines/barrier_diagnostic.py

"""
Conversion Barrier Diagnostic Engine

Takes a bilateral edge (27 alignment dimensions) and the user's behavioral
signals, then diagnoses the PRIMARY barrier preventing conversion.

This is NOT a rules engine. It uses the bilateral alignment gap analysis
from the 3,103 LUXY Ride edges to identify which specific alignment
dimension is furthest below the conversion threshold for this archetype,
then maps that dimension to a BarrierCategory.

The barrier→mechanism mapping is governed by the Bayesian Mechanism
Selection Engine, not by hardcoded rules.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from adam.retargeting.models.enums import (
    ConversionStage, BarrierCategory, RuptureType,
    TherapeuticMechanism, ScaffoldLevel
)
from adam.retargeting.models.diagnostics import (
    AlignmentGap, ConversionBarrierDiagnosis
)


# Alignment dimension → BarrierCategory mapping
# Derived from LUXY Ride bilateral correlation analysis
DIMENSION_BARRIER_MAP: Dict[str, BarrierCategory] = {
    "brand_trust_fit": BarrierCategory.TRUST_DEFICIT,
    "regulatory_fit_score": BarrierCategory.REGULATORY_MISMATCH,
    "processing_route_match": BarrierCategory.PROCESSING_OVERLOAD,
    "emotional_resonance": BarrierCategory.EMOTIONAL_DISCONNECT,
    "anchor_susceptibility_match": BarrierCategory.PRICE_FRICTION,
    "spending_pain_match": BarrierCategory.PRICE_FRICTION,
    "evolutionary_motive_match": BarrierCategory.MOTIVE_MISMATCH,
    "negativity_bias_match": BarrierCategory.NEGATIVITY_BLOCK,
    "persuasion_reactance_match": BarrierCategory.REACTANCE_TRIGGERED,
    "personality_brand_alignment": BarrierCategory.IDENTITY_MISALIGNMENT,
    "optimal_distinctiveness_fit": BarrierCategory.IDENTITY_MISALIGNMENT,
    "composite_alignment": BarrierCategory.INTENTION_ACTION_GAP,
}

# Conversion thresholds per archetype (from LUXY Ride analysis)
# These are the minimum alignment scores at which conversion probability > 50%
ARCHETYPE_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "status_seeker": {
        "brand_trust_fit": 0.471,
        "regulatory_fit_score": 0.091,
        "emotional_resonance": 0.480,
        "personality_brand_alignment": 0.600,
        "evolutionary_motive_match": 0.450,
    },
    "careful_truster": {
        "brand_trust_fit": 0.428,  # THE single strongest predictor (r=+0.619)
        "emotional_resonance": 0.501,
        "negativity_bias_match": 0.169,  # INVERTED: lower = better
        "processing_route_match": 0.550,
        "anchor_susceptibility_match": 0.400,
    },
    "easy_decider": {
        "processing_route_match": 0.618,  # THE single strongest predictor (d=+1.364)
        "evolutionary_motive_match": 0.500,
        "composite_alignment": 0.550,
    },
}


class ConversionBarrierDiagnosticEngine:
    """
    Diagnoses the primary conversion barrier for a non-converting user.
    
    Architecture:
    1. Classify conversion stage from behavioral signals
    2. Detect any engagement rupture
    3. Compute alignment gaps from bilateral edge
    4. Identify primary barrier (largest gap × importance weight)
    5. Estimate reactance, PKM phase, and ownership levels
    6. Recommend mechanism via Bayesian selection
    """
    
    def __init__(self, neo4j_driver, mechanism_selector, stage_classifier):
        self.driver = neo4j_driver
        self.mechanism_selector = mechanism_selector
        self.stage_classifier = stage_classifier
    
    async def diagnose(
        self,
        user_id: str,
        brand_id: str,
        archetype_id: str,
        bilateral_edge: Dict[str, float],  # 27 alignment dimensions
        behavioral_signals: Dict[str, float],
        touch_history: List[Dict],
    ) -> ConversionBarrierDiagnosis:
        """
        Produce a complete barrier diagnosis.
        
        Args:
            user_id: The user being diagnosed
            brand_id: The brand they haven't converted for
            archetype_id: Their classified archetype
            bilateral_edge: The 27-dimensional alignment vector
            behavioral_signals: Recent behavioral data (page views, dwell, clicks, etc.)
            touch_history: Previous therapeutic touches and outcomes
            
        Returns:
            ConversionBarrierDiagnosis with recommended mechanism
        """
        # Step 1: Stage classification
        stage, stage_confidence, stage_signals = (
            await self.stage_classifier.classify(behavioral_signals, touch_history)
        )
        
        # Step 2: Rupture detection
        rupture_type, rupture_severity = self._detect_rupture(
            behavioral_signals, touch_history
        )
        
        # Step 3: Compute alignment gaps
        thresholds = ARCHETYPE_THRESHOLDS.get(archetype_id, {})
        alignment_gaps = self._compute_alignment_gaps(
            bilateral_edge, thresholds, archetype_id
        )
        
        # Step 4: Identify primary barrier
        primary_barrier, primary_gaps = self._identify_primary_barrier(
            alignment_gaps, stage
        )
        
        # Step 5: Estimate psychological states
        reactance_level = self._estimate_reactance(touch_history)
        reactance_budget = max(0.0, 1.0 - reactance_level)
        pk_phase = self._estimate_pk_phase(touch_history)
        ownership = self._estimate_ownership(behavioral_signals)
        
        # Step 6: Select mechanism
        recommended_mechanism, confidence, rationale = (
            await self.mechanism_selector.select(
                barrier=primary_barrier,
                archetype_id=archetype_id,
                stage=stage,
                reactance_level=reactance_level,
                pk_phase=pk_phase,
                ownership_level=ownership,
                touch_history=touch_history,
            )
        )
        
        # Step 7: Determine scaffold level
        scaffold_level = self._determine_scaffold_level(
            stage, len(touch_history), pk_phase
        )
        
        return ConversionBarrierDiagnosis(
            user_id=user_id,
            brand_id=brand_id,
            archetype_id=archetype_id,
            conversion_stage=stage,
            stage_confidence=stage_confidence,
            stage_signals=stage_signals,
            rupture_type=rupture_type,
            rupture_severity=rupture_severity,
            primary_barrier=primary_barrier,
            primary_barrier_confidence=confidence,
            primary_alignment_gaps=primary_gaps,
            estimated_reactance_level=reactance_level,
            reactance_budget_remaining=reactance_budget,
            persuasion_knowledge_phase=pk_phase,
            ownership_level=ownership,
            ownership_decay_rate=self._ownership_decay(behavioral_signals),
            total_touches_received=len(touch_history),
            touches_since_last_engagement=self._touches_since_engagement(touch_history),
            last_mechanism_deployed=self._last_mechanism(touch_history),
            last_mechanism_outcome=self._last_outcome(touch_history),
            recommended_mechanism=recommended_mechanism,
            recommended_scaffold_level=scaffold_level,
            mechanism_confidence=confidence,
            mechanism_rationale=rationale,
        )
    
    def _compute_alignment_gaps(
        self,
        bilateral_edge: Dict[str, float],
        thresholds: Dict[str, float],
        archetype_id: str,
    ) -> List[AlignmentGap]:
        """Compute gaps between actual alignment and conversion thresholds."""
        gaps = []
        for dim, threshold in thresholds.items():
            actual = bilateral_edge.get(dim, 0.0)
            
            # For negativity_bias_match, HIGHER = WORSE (inverted)
            if dim == "negativity_bias_match":
                gap_mag = actual - threshold  # positive = too much negativity
            else:
                gap_mag = threshold - actual  # positive = deficit
            
            if gap_mag > 0:  # Only include actual deficits
                gaps.append(AlignmentGap(
                    dimension=dim,
                    actual_value=actual,
                    threshold_value=threshold,
                    gap_magnitude=gap_mag,
                    effect_size_d=gap_mag / 0.15,  # approximate SD from LUXY data
                    rank_in_archetype=0,  # filled below
                ))
        
        # Rank by gap magnitude
        gaps.sort(key=lambda g: g.gap_magnitude, reverse=True)
        for i, gap in enumerate(gaps):
            gap.rank_in_archetype = i + 1
        
        return gaps
    
    def _identify_primary_barrier(
        self,
        alignment_gaps: List[AlignmentGap],
        stage: ConversionStage,
    ) -> Tuple[BarrierCategory, List[AlignmentGap]]:
        """Identify the primary barrier from alignment gaps."""
        if not alignment_gaps:
            # No alignment gaps but didn't convert = intention-action gap
            return BarrierCategory.INTENTION_ACTION_GAP, []
        
        primary_dim = alignment_gaps[0].dimension
        primary_barrier = DIMENSION_BARRIER_MAP.get(
            primary_dim, BarrierCategory.INTENTION_ACTION_GAP
        )
        
        # Collect all gaps contributing to this barrier category
        contributing_gaps = [
            g for g in alignment_gaps
            if DIMENSION_BARRIER_MAP.get(g.dimension) == primary_barrier
        ]
        
        return primary_barrier, contributing_gaps
    
    def _detect_rupture(
        self,
        behavioral_signals: Dict[str, float],
        touch_history: List[Dict],
    ) -> Tuple[RuptureType, float]:
        """Detect engagement ruptures using Safran & Muran typology."""
        if not touch_history:
            return RuptureType.NONE, 0.0
        
        # Withdrawal detection: engagement velocity decline
        recent_engagements = [
            t.get("engagement_occurred", False)
            for t in touch_history[-3:]
        ]
        if len(recent_engagements) >= 3 and not any(recent_engagements):
            return RuptureType.WITHDRAWAL, 0.7
        
        # Decay detection: time since last engagement
        last_engagement_idx = None
        for i in range(len(touch_history) - 1, -1, -1):
            if touch_history[i].get("engagement_occurred"):
                last_engagement_idx = i
                break
        
        if last_engagement_idx is not None:
            touches_since = len(touch_history) - 1 - last_engagement_idx
            if touches_since >= 3:
                return RuptureType.DECAY, min(1.0, touches_since * 0.2)
        
        # Confrontation detection: explicit negative signal
        if behavioral_signals.get("unsubscribe_signal", 0) > 0:
            return RuptureType.CONFRONTATION, 0.9
        
        return RuptureType.NONE, 0.0
    
    def _estimate_reactance(self, touch_history: List[Dict]) -> float:
        """
        Estimate cumulative reactance using Wicklund's hydraulic model.
        
        Each touch adds reactance. Time between touches allows decay.
        Rapid-fire touches compound MULTIPLICATIVELY.
        """
        if not touch_history:
            return 0.0
        
        reactance = 0.0
        decay_rate = 0.15  # per 24h
        
        for i, touch in enumerate(touch_history):
            # Add reactance from this touch
            touch_reactance = 0.1  # base per touch
            
            # Increase if touch was ignored
            if not touch.get("engagement_occurred", False):
                touch_reactance *= 1.5
            
            # Hydraulic compounding: less time between touches = multiplicative
            if i > 0:
                hours_gap = touch.get("hours_since_previous", 24)
                if hours_gap < 12:
                    touch_reactance *= 2.0  # Wicklund: compound if not dissipated
                elif hours_gap < 24:
                    touch_reactance *= 1.3
            
            reactance += touch_reactance
            
            # Decay since this touch
            hours_since = touch.get("hours_since_delivery", 0)
            days_since = hours_since / 24.0
            reactance *= max(0.0, 1.0 - (decay_rate * days_since))
        
        return min(1.0, reactance)
    
    def _estimate_pk_phase(self, touch_history: List[Dict]) -> int:
        """Estimate Persuasion Knowledge Model phase from touch count."""
        n_touches = len(touch_history)
        if n_touches <= 2:
            return 1  # Peripheral, PK not activated
        elif n_touches <= 5:
            return 2  # PK activated, hostile central processing
        else:
            return 3  # Full coping responses
    
    def _estimate_ownership(self, behavioral_signals: Dict[str, float]) -> float:
        """Estimate psychological ownership from browsing behavior."""
        ownership = 0.0
        
        # Control: interactions with configurator/booking flow
        ownership += behavioral_signals.get("booking_steps_completed", 0) * 0.2
        
        # Self-investment: time spent on site
        total_dwell_minutes = behavioral_signals.get("total_dwell_minutes", 0)
        ownership += min(0.3, total_dwell_minutes * 0.05)
        
        # Intimate knowing: pages viewed, reviews read
        pages = behavioral_signals.get("pages_viewed", 0)
        ownership += min(0.3, pages * 0.05)
        
        # Decay over time
        hours_since_last_visit = behavioral_signals.get("hours_since_last_visit", 0)
        decay = 0.05 * hours_since_last_visit  # 5% per hour
        ownership = max(0.0, ownership - decay)
        
        return min(1.0, ownership)
    
    def _determine_scaffold_level(
        self,
        stage: ConversionStage,
        touch_count: int,
        pk_phase: int,
    ) -> ScaffoldLevel:
        """Map stage + touch count to scaffold level."""
        if stage == ConversionStage.CURIOUS:
            return ScaffoldLevel.RECRUITMENT
        elif stage == ConversionStage.EVALUATING:
            if pk_phase <= 1:
                return ScaffoldLevel.SIMPLIFICATION
            else:
                return ScaffoldLevel.DIRECTION_MAINTENANCE
        elif stage == ConversionStage.INTENDING:
            return ScaffoldLevel.FRUSTRATION_CONTROL
        elif stage == ConversionStage.STALLED:
            return ScaffoldLevel.DEMONSTRATION
        else:
            return ScaffoldLevel.RECRUITMENT
    
    def _ownership_decay(self, signals: Dict) -> float:
        return signals.get("hours_since_last_visit", 0) * 0.05
    
    def _touches_since_engagement(self, history: List[Dict]) -> int:
        count = 0
        for t in reversed(history):
            if t.get("engagement_occurred"):
                break
            count += 1
        return count
    
    def _last_mechanism(self, history: List[Dict]) -> Optional[TherapeuticMechanism]:
        if history:
            m = history[-1].get("mechanism")
            if m:
                return TherapeuticMechanism(m)
        return None
    
    def _last_outcome(self, history: List[Dict]) -> Optional[str]:
        if history:
            return history[-1].get("outcome")
        return None
```

<a name="section-e2"></a>
## E.2 Mechanism Selection Engine (Bayesian)

```python
# adam/retargeting/engines/mechanism_selector.py

"""
Bayesian Mechanism Selection Engine

Uses Thompson Sampling to select which therapeutic mechanism to deploy
for a given barrier × archetype × personality profile.

Each (mechanism, barrier, archetype) triple has a Beta(α, β) prior.
Initial priors are seeded from the research effect sizes in Section A.2.
Each touch outcome updates the posterior: success → α+1, failure → β+1.

Thompson Sampling naturally balances exploitation (use what works)
with exploration (try uncertain mechanisms to learn).
"""

import numpy as np
from typing import Dict, List, Optional, Tuple

from adam.retargeting.models.enums import (
    BarrierCategory, TherapeuticMechanism, ConversionStage
)
from adam.retargeting.research_priors import RESEARCH_EFFECT_SIZES
from adam.retargeting.personality_mechanism_matrix import PERSONALITY_MECHANISM_SUSCEPTIBILITY


# Which mechanisms can address which barriers
BARRIER_MECHANISM_CANDIDATES: Dict[BarrierCategory, List[TherapeuticMechanism]] = {
    BarrierCategory.TRUST_DEFICIT: [
        TherapeuticMechanism.CLAUDE_ARGUMENT,  # Highest priority: generates novel factual evidence
        TherapeuticMechanism.EVIDENCE_PROOF,
        TherapeuticMechanism.SOCIAL_PROOF_MATCHED,
        TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
    ],
    BarrierCategory.REGULATORY_MISMATCH: [
        TherapeuticMechanism.CLAUDE_ARGUMENT,
        TherapeuticMechanism.CONSTRUAL_SHIFT,
        TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
        TherapeuticMechanism.VIVID_SCENARIO,
    ],
    BarrierCategory.PROCESSING_OVERLOAD: [
        TherapeuticMechanism.FRUSTRATION_CONTROL,
        TherapeuticMechanism.MICRO_COMMITMENT,
        # Note: CLAUDE_ARGUMENT excluded — processing overload requires SIMPLIFICATION,
        # not novel arguments. Adding complexity would worsen the barrier.
    ],
    BarrierCategory.EMOTIONAL_DISCONNECT: [
        TherapeuticMechanism.CLAUDE_ARGUMENT,
        TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
        TherapeuticMechanism.VIVID_SCENARIO,
        TherapeuticMechanism.SOCIAL_PROOF_MATCHED,
    ],
    BarrierCategory.PRICE_FRICTION: [
        TherapeuticMechanism.CLAUDE_ARGUMENT,  # Can generate novel value comparisons
        TherapeuticMechanism.PRICE_ANCHOR,
        TherapeuticMechanism.LOSS_FRAMING,
        TherapeuticMechanism.OWNERSHIP_REACTIVATION,
    ],
    BarrierCategory.MOTIVE_MISMATCH: [
        TherapeuticMechanism.CLAUDE_ARGUMENT,  # Can reframe around correct motive
        TherapeuticMechanism.CONSTRUAL_SHIFT,
        TherapeuticMechanism.VIVID_SCENARIO,
    ],
    BarrierCategory.NEGATIVITY_BLOCK: [
        TherapeuticMechanism.CLAUDE_ARGUMENT,  # Can generate specific counter-evidence
        TherapeuticMechanism.ANXIETY_RESOLUTION,
        TherapeuticMechanism.SOCIAL_PROOF_MATCHED,
        TherapeuticMechanism.EVIDENCE_PROOF,
    ],
    BarrierCategory.REACTANCE_TRIGGERED: [
        TherapeuticMechanism.AUTONOMY_RESTORATION,
        TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
        # Note: CLAUDE_ARGUMENT excluded — reactance-triggered users need LESS pressure,
        # not more sophisticated arguments. Novel argumentation reads as harder sell.
    ],
    BarrierCategory.IDENTITY_MISALIGNMENT: [
        TherapeuticMechanism.CLAUDE_ARGUMENT,
        TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
        TherapeuticMechanism.SOCIAL_PROOF_MATCHED,
    ],
    BarrierCategory.INTENTION_ACTION_GAP: [
        TherapeuticMechanism.IMPLEMENTATION_INTENTION,
        TherapeuticMechanism.OWNERSHIP_REACTIVATION,
        TherapeuticMechanism.LOSS_FRAMING,
        TherapeuticMechanism.MICRO_COMMITMENT,
        # Note: CLAUDE_ARGUMENT excluded — intention-action gap is not an argument
        # problem. The user already wants the product. They need behavioral triggers,
        # not more reasons to want it.
    ],
}


class BayesianMechanismSelector:
    """
    Selects the optimal therapeutic mechanism using Thompson Sampling.
    
    Priors are initialized from research effect sizes (Section A.2).
    Posteriors are updated from observed outcomes via Gradient Bridge.
    
    Personality interaction weights modify the sampling:
    if a mechanism is +1 susceptible for the user's dominant trait,
    the effective alpha is multiplied by 1.5 (50% bonus).
    If -1 resistant, alpha is multiplied by 0.5 (50% penalty).
    """
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    async def select(
        self,
        barrier: BarrierCategory,
        archetype_id: str,
        stage: ConversionStage,
        reactance_level: float,
        pk_phase: int,
        ownership_level: float,
        touch_history: List[Dict],
        user_personality: Optional[Dict[str, float]] = None,
    ) -> Tuple[TherapeuticMechanism, float, str]:
        """
        Select mechanism via Thompson Sampling with personality modulation.
        
        Returns:
            (mechanism, confidence, rationale)
        """
        candidates = BARRIER_MECHANISM_CANDIDATES.get(barrier, [])
        if not candidates:
            return (
                TherapeuticMechanism.EVIDENCE_PROOF,
                0.3,
                "No specific candidates for barrier; defaulting to evidence"
            )
        
        # Filter out recently-failed mechanisms
        recent_failures = {
            t.get("mechanism") for t in touch_history[-2:]
            if not t.get("engagement_occurred", False)
        }
        candidates = [m for m in candidates if m.value not in recent_failures] or candidates
        
        # Filter by reactance constraints
        if reactance_level > 0.7:
            # High reactance: only use autonomy-preserving mechanisms
            autonomy_safe = {
                TherapeuticMechanism.AUTONOMY_RESTORATION,
                TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
                TherapeuticMechanism.SOCIAL_PROOF_MATCHED,
                TherapeuticMechanism.EVIDENCE_PROOF,
            }
            candidates = [m for m in candidates if m in autonomy_safe] or candidates
        
        # Thompson Sampling
        best_mechanism = None
        best_sample = -1.0
        samples = {}
        
        for mechanism in candidates:
            alpha, beta = await self._get_prior(mechanism, barrier, archetype_id)
            
            # Personality modulation
            if user_personality:
                alpha = self._apply_personality_modulation(
                    alpha, mechanism, user_personality
                )
            
            # PKM phase modulation
            if pk_phase >= 2 and mechanism in {
                TherapeuticMechanism.MICRO_COMMITMENT,
                TherapeuticMechanism.LOSS_FRAMING,
            }:
                alpha *= 0.7  # These feel more "salesy" under PK scrutiny
            
            # Draw from Beta posterior
            sample = np.random.beta(alpha, beta)
            samples[mechanism] = sample
            
            if sample > best_sample:
                best_sample = sample
                best_mechanism = mechanism
        
        # Compute confidence from posterior mean
        alpha, beta = await self._get_prior(best_mechanism, barrier, archetype_id)
        confidence = alpha / (alpha + beta)
        
        # Generate rationale
        rationale = self._generate_rationale(
            best_mechanism, barrier, archetype_id, confidence, samples
        )
        
        return best_mechanism, confidence, rationale
    
    async def _get_prior(
        self,
        mechanism: TherapeuticMechanism,
        barrier: BarrierCategory,
        archetype_id: str,
    ) -> Tuple[float, float]:
        """Get Beta(α, β) prior from Neo4j, or initialize from research."""
        # Try Neo4j first
        result = await self._query_prior(mechanism, barrier, archetype_id)
        if result:
            return result["alpha"], result["beta"]
        
        # Initialize from research effect sizes
        # Convert effect size to Beta parameters
        # Higher effect size → higher α relative to β
        base_alpha = 2.0  # weak prior
        base_beta = 2.0
        
        return base_alpha, base_beta
    
    def _apply_personality_modulation(
        self,
        alpha: float,
        mechanism: TherapeuticMechanism,
        personality: Dict[str, float],
    ) -> float:
        """Modulate alpha based on Big Five × mechanism susceptibility."""
        modulated_alpha = alpha
        
        # Find dominant traits
        trait_map = {
            "openness": personality.get("openness", 0.5),
            "conscientiousness": personality.get("conscientiousness", 0.5),
            "extraversion": personality.get("extraversion", 0.5),
            "agreeableness": personality.get("agreeableness", 0.5),
            "neuroticism": personality.get("neuroticism", 0.5),
        }
        
        # Map Cialdini mechanisms to our TherapeuticMechanism enum
        mechanism_to_cialdini = {
            TherapeuticMechanism.SOCIAL_PROOF_MATCHED: "social_proof",
            TherapeuticMechanism.EVIDENCE_PROOF: "authority",
            TherapeuticMechanism.MICRO_COMMITMENT: "commitment",
            TherapeuticMechanism.LOSS_FRAMING: "scarcity",
            TherapeuticMechanism.NARRATIVE_TRANSPORTATION: "narrative",
            TherapeuticMechanism.AUTONOMY_RESTORATION: "autonomy_support",
        }
        
        cialdini_key = mechanism_to_cialdini.get(mechanism)
        if not cialdini_key:
            return modulated_alpha
        
        for trait_name, trait_value in trait_map.items():
            if trait_value > 0.65:
                key = f"{trait_name}_high"
            elif trait_value < 0.35:
                key = f"{trait_name}_low"
            else:
                continue
            
            susceptibility = PERSONALITY_MECHANISM_SUSCEPTIBILITY.get(key, {})
            direction = susceptibility.get(cialdini_key, 0)
            
            if direction == 1:
                modulated_alpha *= 1.3  # susceptible
            elif direction == -1:
                modulated_alpha *= 0.7  # resistant
        
        return modulated_alpha
    
    def _generate_rationale(
        self,
        mechanism: TherapeuticMechanism,
        barrier: BarrierCategory,
        archetype_id: str,
        confidence: float,
        samples: Dict,
    ) -> str:
        """Generate human-readable rationale for mechanism selection."""
        sorted_samples = sorted(samples.items(), key=lambda x: x[1], reverse=True)
        top3 = [(m.value, f"{s:.3f}") for m, s in sorted_samples[:3]]
        
        return (
            f"For {barrier.value} barrier in {archetype_id}: "
            f"Selected {mechanism.value} (confidence={confidence:.2f}). "
            f"Thompson samples: {top3}. "
            f"Posterior mean favors {mechanism.value} given observed outcomes "
            f"for this barrier × archetype combination."
        )
    
    async def _query_prior(self, mechanism, barrier, archetype_id):
        """Query Neo4j for existing prior. Returns None if not found."""
        # Implementation: run QUERIES["get_mechanism_prior"]
        pass  # Implemented in Session 33-3
```

---

# SECTION F: INTEGRATION LAYER

<a name="section-f1"></a>
## F.1 FastAPI Endpoints

```python
# adam/retargeting/api.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

router = APIRouter(prefix="/api/v1/retargeting", tags=["Therapeutic Retargeting"])


@router.post("/diagnose", response_model=ConversionBarrierDiagnosis)
async def diagnose_conversion_barrier(
    user_id: str,
    brand_id: str,
    archetype_id: str,
    bilateral_edge: Dict[str, float],
    behavioral_signals: Dict[str, float],
):
    """
    Diagnose why a specific user has not converted.
    
    Takes the bilateral alignment edge and behavioral signals,
    returns a complete barrier diagnosis with recommended mechanism.
    
    Latency target: <200ms (graph query + classification + selection)
    """
    pass


@router.post("/sequence/create", response_model=TherapeuticSequence)
async def create_therapeutic_sequence(
    user_id: str,
    brand_id: str,
    archetype_id: str,
    initial_diagnosis: ConversionBarrierDiagnosis,
):
    """
    Create a new therapeutic retargeting sequence.
    
    Initializes the sequence with the first touch based on
    the initial diagnosis. Subsequent touches are determined
    adaptively based on outcomes.
    """
    pass


@router.post("/sequence/{sequence_id}/next-touch", response_model=TherapeuticTouch)
async def get_next_touch(
    sequence_id: str,
    latest_outcome: Optional[BarrierResolutionOutcome] = None,
):
    """
    Get the next therapeutic touch for an active sequence.
    
    If latest_outcome is provided, updates the diagnosis and
    selects the next mechanism based on the updated state.
    
    This is the core adaptive loop — each call produces a
    touch that is DIFFERENT from the previous one, targeting
    the specific barrier that remains unresolved.
    """
    pass


@router.post("/sequence/{sequence_id}/observe-outcome")
async def observe_outcome(
    sequence_id: str,
    outcome: BarrierResolutionOutcome,
):
    """
    Record an outcome observation for a delivered touch.
    
    Triggers:
    1. Barrier diagnosis update
    2. Mechanism prior Bayesian update (Gradient Bridge)
    3. Reactance level recalculation
    4. Stage reclassification
    5. Rupture detection
    """
    pass


@router.get("/sites/whitelist/{archetype_id}", response_model=List[Dict])
async def get_site_whitelist(
    archetype_id: str,
    min_alignment: float = 0.6,
    max_domains: int = 500,
):
    """
    Get psychologically-aligned domain whitelist for an archetype.
    
    Returns domains whose psychological profile aligns with the
    specified archetype, sorted by alignment score.
    """
    pass


@router.post("/sites/score", response_model=SitePsychologicalProfile)
async def score_site(url: str):
    """
    Crawl and score a website's psychological profile.
    
    Uses Claude to analyze page content and extract 12
    psychological dimensions. Stores result in Neo4j.
    """
    pass


@router.get("/learning/mechanism-effectiveness")
async def get_mechanism_effectiveness(
    mechanism: Optional[TherapeuticMechanism] = None,
    barrier: Optional[BarrierCategory] = None,
    archetype_id: Optional[str] = None,
):
    """
    Query mechanism effectiveness from learned posteriors.
    
    Used for dashboard reporting and system monitoring.
    """
    pass
```

<a name="section-f2"></a>
## F.2 LangGraph Orchestration Workflow

```python
# adam/retargeting/workflows/therapeutic_workflow.py

"""
LangGraph workflow for the Therapeutic Retargeting Loop.

Nodes:
1. diagnose_barrier — Run barrier diagnostic engine
2. select_mechanism — Run Bayesian mechanism selector
3. build_touch — Construct therapeutic touch with creative spec
4. check_rupture — Evaluate if rupture repair is needed
5. check_reactance — Evaluate if reactance budget is exceeded
6. generate_creative — Invoke #15 Copy Generation with mechanism spec
7. observe_outcome — Process outcome and update priors
8. update_sequence — Update sequence state and plan next node
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List


class TherapeuticState(TypedDict):
    user_id: str
    brand_id: str
    archetype_id: str
    bilateral_edge: dict
    behavioral_signals: dict
    touch_history: list
    current_diagnosis: Optional[dict]
    current_touch: Optional[dict]
    sequence: Optional[dict]
    outcome: Optional[dict]
    should_suppress: bool
    should_pause: bool
    error: Optional[str]


def build_therapeutic_workflow() -> StateGraph:
    workflow = StateGraph(TherapeuticState)
    
    # Add nodes
    workflow.add_node("diagnose_barrier", diagnose_barrier_node)
    workflow.add_node("check_rupture", check_rupture_node)
    workflow.add_node("check_reactance", check_reactance_node)
    workflow.add_node("select_mechanism", select_mechanism_node)
    workflow.add_node("build_touch", build_touch_node)
    workflow.add_node("generate_creative", generate_creative_node)
    workflow.add_node("deliver_touch", deliver_touch_node)
    workflow.add_node("observe_outcome", observe_outcome_node)
    workflow.add_node("update_priors", update_priors_node)
    
    # Define edges
    workflow.set_entry_point("diagnose_barrier")
    workflow.add_edge("diagnose_barrier", "check_rupture")
    
    workflow.add_conditional_edges(
        "check_rupture",
        lambda state: "pause" if state.get("should_pause") else "continue",
        {"pause": END, "continue": "check_reactance"},
    )
    
    workflow.add_conditional_edges(
        "check_reactance",
        lambda state: "suppress" if state.get("should_suppress") else "continue",
        {"suppress": END, "continue": "select_mechanism"},
    )
    
    workflow.add_edge("select_mechanism", "build_touch")
    workflow.add_edge("build_touch", "generate_creative")
    workflow.add_edge("generate_creative", "deliver_touch")
    workflow.add_edge("deliver_touch", "observe_outcome")
    workflow.add_edge("observe_outcome", "update_priors")
    workflow.add_edge("update_priors", END)
    
    return workflow.compile()
```

<a name="section-f3"></a>
## F.3 Kafka Event Schemas

```python
# adam/retargeting/events.py

KAFKA_TOPICS = {
    "retargeting.barrier.diagnosed": {
        "schema": "ConversionBarrierDiagnosis",
        "consumers": ["mechanism_selector", "dashboard", "learning_pipeline"],
    },
    "retargeting.touch.created": {
        "schema": "TherapeuticTouch",
        "consumers": ["creative_generator", "delivery_engine", "dashboard"],
    },
    "retargeting.touch.delivered": {
        "schema": "TherapeuticTouch + delivery_metadata",
        "consumers": ["outcome_observer", "reactance_tracker"],
    },
    "retargeting.outcome.observed": {
        "schema": "BarrierResolutionOutcome",
        "consumers": ["prior_updater", "gradient_bridge", "dashboard"],
    },
    "retargeting.sequence.completed": {
        "schema": "SequenceLearningReport",
        "consumers": ["bayesian_hierarchy", "cross_archetype_transfer"],
    },
    "retargeting.rupture.detected": {
        "schema": "RuptureEvent",
        "consumers": ["repair_strategy_selector", "dashboard"],
    },
    "retargeting.site.scored": {
        "schema": "SitePsychologicalProfile",
        "consumers": ["whitelist_generator", "neo4j_writer"],
    },
}
```

<a name="section-f4"></a>
## F.4 Redis Caching Strategy

```python
# adam/retargeting/cache.py

REDIS_CACHE_KEYS = {
    # L1: Hot path — sub-10ms
    "retargeting:diagnosis:{user_id}:{brand_id}": {
        "ttl": 3600,  # 1 hour
        "description": "Latest barrier diagnosis for user × brand",
    },
    "retargeting:sequence:{sequence_id}": {
        "ttl": 86400,  # 24 hours
        "description": "Active sequence state",
    },
    "retargeting:reactance:{user_id}": {
        "ttl": 604800,  # 7 days
        "description": "Cumulative reactance level",
    },
    
    # L2: Warm path — sub-50ms
    "retargeting:prior:{mechanism}:{barrier}:{archetype}": {
        "ttl": 3600,
        "description": "Thompson Sampling prior (alpha, beta)",
    },
    "retargeting:site_whitelist:{archetype_id}": {
        "ttl": 86400,
        "description": "Pre-computed domain whitelist",
    },
    
    # L3: Reference — sub-200ms
    "retargeting:site_profile:{domain}": {
        "ttl": 604800,  # 7 days
        "description": "Site psychological profile",
    },
}
```

<a name="section-f5"></a>
## F.5 Prometheus Metrics

```python
# adam/retargeting/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Diagnostic metrics
DIAGNOSES_TOTAL = Counter(
    "retargeting_diagnoses_total",
    "Total barrier diagnoses performed",
    ["archetype_id", "primary_barrier"]
)
DIAGNOSIS_LATENCY = Histogram(
    "retargeting_diagnosis_latency_seconds",
    "Latency of barrier diagnosis",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
)

# Mechanism metrics
MECHANISM_SELECTIONS = Counter(
    "retargeting_mechanism_selections_total",
    "Mechanisms selected by Thompson Sampling",
    ["mechanism", "barrier", "archetype_id"]
)
MECHANISM_OUTCOMES = Counter(
    "retargeting_mechanism_outcomes_total",
    "Outcomes observed per mechanism",
    ["mechanism", "outcome_type"]  # outcome_type: engaged, ignored, converted
)

# Sequence metrics
ACTIVE_SEQUENCES = Gauge(
    "retargeting_active_sequences",
    "Currently active therapeutic sequences",
    ["archetype_id"]
)
SEQUENCE_CONVERSION_RATE = Gauge(
    "retargeting_sequence_conversion_rate",
    "Conversion rate for completed sequences",
    ["archetype_id"]
)
SEQUENCE_LENGTH = Histogram(
    "retargeting_sequence_length_touches",
    "Number of touches in completed sequences",
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
)

# Rupture metrics
RUPTURES_DETECTED = Counter(
    "retargeting_ruptures_detected_total",
    "Ruptures detected by type",
    ["rupture_type", "archetype_id"]
)
RUPTURE_REPAIR_SUCCESS = Counter(
    "retargeting_rupture_repairs_total",
    "Rupture repair outcomes",
    ["rupture_type", "repaired"]
)

# Reactance metrics
REACTANCE_SUPPRESSIONS = Counter(
    "retargeting_reactance_suppressions_total",
    "Sequences suppressed due to reactance budget",
    ["archetype_id"]
)

# Site scoring metrics
SITES_SCORED = Counter(
    "retargeting_sites_scored_total",
    "Sites psychologically profiled"
)
```

---

# SECTION G: CLAUDE CODE SESSION PLAN

<a name="session-1"></a>
## Session 33-1: Barrier Diagnostic Models + Neo4j Schema
**Duration**: 3-4 hours
**Objective**: Establish all Pydantic models and Neo4j schema for the therapeutic retargeting system.

**System Prompt for Claude Code**:
```
You are building the data foundation for INFORMATIV's Therapeutic Retargeting Engine — Enhancement #33.

CONTEXT: INFORMATIV has bilateral psychological intelligence: 65 buyer dimensions × 65 seller dimensions × 27 alignment dimensions. The retargeting system diagnoses WHY someone didn't convert at a mechanistic level and deploys the specific intervention to resolve that barrier.

This session builds ALL Pydantic models and the Neo4j schema. The models are in the deployment directive Section C (all subsections). The Neo4j schema is in Section D.

EXISTING PATTERNS:
- All models use Pydantic v2 with Field descriptions
- Neo4j schema follows the ConversionEdge intermediate-node pattern from Enhancement #32
- Constants go in adam/constants.py
- Enums use str,Enum pattern

FILES TO CREATE:
- adam/retargeting/__init__.py
- adam/retargeting/models/__init__.py
- adam/retargeting/models/enums.py — ConversionStage, RuptureType, ScaffoldLevel, BarrierCategory, TherapeuticMechanism
- adam/retargeting/models/diagnostics.py — AlignmentGap, ConversionBarrierDiagnosis, BarrierResolutionOutcome
- adam/retargeting/models/sequences.py — TherapeuticTouch, TherapeuticSequence, SequenceDecisionNode
- adam/retargeting/models/site_profiles.py — SitePsychologicalProfile, SiteArchetypeAlignment
- adam/retargeting/models/learning.py — MechanismEffectivenessSignal, SequenceLearningReport
- adam/retargeting/research_priors.py — RESEARCH_EFFECT_SIZES dict
- adam/retargeting/personality_mechanism_matrix.py — PERSONALITY_MECHANISM_SUSCEPTIBILITY
- adam/retargeting/schema/neo4j_schema.cypher — Full schema DDL
- adam/retargeting/schema/queries.py — Key Cypher query templates
- tests/retargeting/test_models.py — Model validation tests

COPY THE MODELS EXACTLY FROM THE DEPLOYMENT DIRECTIVE. Do not simplify or abbreviate.
```

**Deliverables**: All model files, schema files, research priors, personality matrix, model tests.

---

<a name="session-2"></a>
## Session 33-2: Stage Classification Engine
**Duration**: 2-3 hours
**Objective**: Build the TTM-derived conversion stage classifier using behavioral signals.

**System Prompt for Claude Code**:
```
You are building the Conversion Stage Classification Engine for INFORMATIV's Therapeutic Retargeting Engine.

CONTEXT: This engine classifies users into 6 conversion stages (UNAWARE, CURIOUS, EVALUATING, INTENDING, STALLED, CONVERTED) from behavioral signals — NOT self-report. The stage determines which therapeutic mechanisms are appropriate. Stage-mismatched interventions generate resistance (TTM research).

The classifier uses:
1. Pixel fire signals (page views, dwell time, booking flow progress)
2. Engagement velocity (rate of change in engagement metrics)
3. Recency-weighted interaction history
4. Comparison behavior signals (competitor site visits)

The key insight from Krebs et al. (2010): dynamically re-tailored interventions that iteratively reassess outperform static segmentation. This classifier runs EVERY TIME a new behavioral signal arrives.

DEPENDS ON: Enhancement #10 (Journey Tracking) state detection infrastructure.
Must integrate with the JourneyTracker.update_journey() pattern.

FILES TO CREATE:
- adam/retargeting/engines/__init__.py
- adam/retargeting/engines/stage_classifier.py
- adam/retargeting/engines/signal_processors.py — behavioral signal preprocessing
- tests/retargeting/test_stage_classifier.py
```

---

<a name="session-3"></a>
## Session 33-3: Mechanism Selection Engine
**Duration**: 3-4 hours
**Objective**: Build the Bayesian Thompson Sampling mechanism selector.

**System Prompt for Claude Code**:
```
You are building the Bayesian Mechanism Selection Engine for INFORMATIV's Therapeutic Retargeting Engine.

CONTEXT: This engine selects which therapeutic mechanism to deploy for a given barrier × archetype × personality profile. It uses Thompson Sampling with Beta(α, β) priors initialized from research effect sizes (see RESEARCH_EFFECT_SIZES in research_priors.py).

Key architectural decisions:
1. Each (mechanism, barrier, archetype) triple has its own Beta prior in Neo4j
2. Personality modulation: Big Five × Cialdini susceptibility matrix adjusts α
3. Reactance constraint: high reactance filters to autonomy-safe mechanisms only
4. PKM phase constraint: Phase 2-3 penalizes "salesy" mechanisms
5. Recent-failure filter: don't re-deploy a mechanism that just failed
6. Thompson Sampling naturally balances explore/exploit

The full engine code is in Section E.2 of the deployment directive.

FILES TO CREATE:
- adam/retargeting/engines/mechanism_selector.py
- adam/retargeting/engines/prior_manager.py — Neo4j prior CRUD
- tests/retargeting/test_mechanism_selector.py
```

---

<a name="session-4"></a>
## Session 33-4: Rupture Detection System
**Duration**: 2-3 hours
**Objective**: Build the Safran & Muran-inspired rupture detection and repair strategy system.

**System Prompt for Claude Code**:
```
You are building the Rupture Detection System for INFORMATIV's Therapeutic Retargeting Engine.

CONTEXT: From therapeutic alliance research (Eubanks et al., 2018), successful rupture resolution (d=.62) produces STRONGER outcomes than never having a rupture. The system must detect both:
- WITHDRAWAL ruptures (silent disengagement — declining engagement, ad blindness)
- CONFRONTATION ruptures (active rejection — unsubscribes, complaints)
- DECAY ruptures (gradual fading without clear trigger)

Repair strategies differ by rupture type:
- Withdrawal: Change mechanism completely. Do NOT acknowledge explicitly.
- Confrontation: Transparent acknowledgment + changed approach.
- Decay: Re-engagement with novel content. Reset narrative arc.

The Wicklund hydraulic model governs reactance compounding — rapid touches after rupture compound reactance multiplicatively.

FILES TO CREATE:
- adam/retargeting/engines/rupture_detector.py
- adam/retargeting/engines/repair_strategy.py
- tests/retargeting/test_rupture_detection.py
```

---

<a name="session-5"></a>
## Session 33-5: Site Crawl and Psychological Scoring
**Duration**: 3-4 hours
**Objective**: Build the pipeline that crawls websites and scores them on 12 psychological dimensions.

**System Prompt for Claude Code**:
```
You are building the Site Psychological Scoring Pipeline for INFORMATIV's Therapeutic Retargeting Engine.

CONTEXT: INFORMATIV needs to dynamically generate domain whitelists for each buyer archetype. A Status Seeker should see ads on high-aspirational, low-urgency sites. A Careful Truster should see ads on high-rational-density, high-trust-signaling sites.

The pipeline:
1. Accepts a URL or domain list
2. Crawls the page (respecting robots.txt, rate limits)
3. Extracts text content and visual signals
4. Sends content to Claude for psychological dimension scoring (12 dimensions)
5. Computes archetype alignment scores
6. Stores SitePsychProfile nodes in Neo4j
7. Generates domain whitelists per archetype

The 12 dimensions are defined in Section C.4 SitePsychologicalProfile model.

The Claude prompt for scoring should be structured as a JSON extraction task with the 12 dimensions, each scored 0.0-1.0 with brief justification.

IMPORTANT: This must handle batch processing for the initial crawl of all target domains AND incremental scoring for new domains.

FILES TO CREATE:
- adam/retargeting/engines/site_crawler.py — async web crawler with rate limiting
- adam/retargeting/engines/site_scorer.py — Claude-based psychological scoring
- adam/retargeting/engines/whitelist_generator.py — archetype × site alignment
- adam/retargeting/prompts/site_scoring_prompt.py — structured Claude prompt
- tests/retargeting/test_site_scoring.py
```

---

<a name="session-6"></a>
## Session 33-6: Therapeutic Sequence Orchestrator
**Duration**: 4-5 hours
**Objective**: Build the core orchestration engine that manages therapeutic sequences adaptively.

**System Prompt for Claude Code**:
```
You are building the Therapeutic Sequence Orchestrator — the brain of INFORMATIV's retargeting system.

CONTEXT: This is NOT a linear sequence engine. It is a DECISION TREE orchestrator. After each touch:
1. Observe outcome (engaged? stage advanced? converted? new barrier?)
2. Update barrier diagnosis
3. Check for ruptures
4. Check reactance budget
5. Select next mechanism via Thompson Sampling
6. Build next touch with appropriate scaffold level and construal shift
7. Manage narrative arc position
8. Handle cross-archetype reclassification signals

The orchestrator must enforce all suppression rules:
- Max touches before suppression
- CTR floor triggers
- Reactance budget exhaustion
- Temporal spacing (min/max hours between touches)
- Post-conversion suppression

INTEGRATES WITH:
- Enhancement #10 (Journey Tracking) for state management
- Enhancement #15 (Copy Generation) for creative spec generation
- Enhancement #06 (Gradient Bridge) for learning signal propagation
- Enhancement #02 (Blackboard) for cross-component state sharing

The full LangGraph workflow is in Section F.2.

FILES TO CREATE:
- adam/retargeting/engines/sequence_orchestrator.py — core orchestration logic
- adam/retargeting/engines/touch_builder.py — construct TherapeuticTouch from diagnosis
- adam/retargeting/engines/narrative_manager.py — narrative arc tracking
- adam/retargeting/engines/suppression_controller.py — all suppression rules
- adam/retargeting/workflows/therapeutic_workflow.py — LangGraph workflow
- tests/retargeting/test_orchestrator.py
```

---

<a name="session-7"></a>
## Session 33-7: Narrative Arc Generator
**Duration**: 2-3 hours
**Objective**: Build the system that structures retargeting sequences as episodic narratives.

**System Prompt for Claude Code**:
```
You are building the Narrative Arc Generator for INFORMATIV's Therapeutic Retargeting Engine.

CONTEXT: From narrative transportation research (Van Laer et al., 2014): transportation reduces critical thoughts (r=-.20) and effects are STRONGER for commercial stories. Sequential retargeting should be structured as an unfolding story, not discrete ad impressions.

The narrative arc has 5 chapters:
1. INTRODUCTION — Establish the character (matched testimonial or scenario)
2. COMPLICATION — Present the problem the user shares with the character
3. RISING_ACTION — Show the character's consideration process
4. RESOLUTION — Show the character's positive outcome with the product
5. EPILOGUE — Social proof / outcome confirmation

Each retargeting touch maps to a narrative chapter. The system selects:
- Testimonial model type (coping vs mastery per Braaksma et al.)
- Character similarity to user archetype
- Evidence type (narrative-first for early chapters, statistical for later)
- Construal level progression (abstract→concrete across the arc)

Three arc types per archetype:
- RESOLUTION: Problem→Solution (Careful Truster)
- DISCOVERY: Curiosity→Reward (Status Seeker)
- TRANSFORMATION: Before→After (Easy Decider)

FILES TO CREATE:
- adam/retargeting/engines/narrative_arc.py
- adam/retargeting/engines/testimonial_matcher.py
- adam/retargeting/prompts/narrative_prompts.py
- tests/retargeting/test_narrative_arc.py
```

---

<a name="session-8"></a>
## Session 33-8: Learning Loop and Gradient Bridge Integration
**Duration**: 3-4 hours
**Objective**: Build the feedback loop that propagates outcomes back through the Bayesian hierarchy.

**System Prompt for Claude Code**:
```
You are building the Learning Loop for INFORMATIV's Therapeutic Retargeting Engine.

CONTEXT: Every therapeutic touch outcome generates a MechanismEffectivenessSignal that:
1. Updates the Thompson Sampling posterior for (mechanism, barrier, archetype)
2. Propagates through the Gradient Bridge (#06) to update cross-archetype priors
3. Updates personality × mechanism interaction weights
4. Generates a SequenceLearningReport when the sequence completes

The Bayesian hierarchy (from Enhancement #32):
- Corpus prior → Category prior → Brand prior → Campaign prior
- Each level inherits from the level above
- Mechanism effectiveness is learned at ALL levels simultaneously

The key hypothesis from the retargeting_strategy.json that this system TESTS:
"Each subsequent touch should convert at a HIGHER rate than the previous
(because it addresses a more specific failure). If touch N converts lower
than touch N-1, the mechanism mapping is wrong for that archetype."

This session also builds the Kafka event producers for all learning signals.

FILES TO CREATE:
- adam/retargeting/engines/learning_loop.py — outcome processing and prior updates
- adam/retargeting/engines/gradient_bridge_adapter.py — #06 integration
- adam/retargeting/events.py — Kafka event schemas and producers
- adam/retargeting/engines/sequence_reporter.py — SequenceLearningReport generation
- tests/retargeting/test_learning_loop.py
```

---

<a name="session-9"></a>
## Session 33-9: StackAdapt Campaign Translation Layer
**Duration**: 3-4 hours
**Objective**: Translate therapeutic sequences into StackAdapt-executable campaign configurations.

**System Prompt for Claude Code**:
```
You are building the StackAdapt Campaign Translation Layer for INFORMATIV's Therapeutic Retargeting Engine.

CONTEXT: The therapeutic retargeting engine produces TherapeuticSequence objects with per-touch mechanism specifications, creative strategies, domain whitelists, frequency caps, and timing rules. This layer translates those into StackAdapt's native campaign configuration format.

Translation mapping:
- TherapeuticSequence → StackAdapt Campaign Group (one per archetype)
- TherapeuticTouch → StackAdapt Campaign (sequential with audience exclusion)
- Domain whitelists → StackAdapt Site Targeting (CSV upload format)
- Frequency caps → StackAdapt Campaign Settings
- Dayparting → StackAdapt Scheduling grid
- Creative specs → StackAdapt Creative assets (headline, body, CTA, image)
- Retargeting audiences → StackAdapt Pixel-based audience segments
- Suppression lists → StackAdapt Exclusion audiences

Output format: A complete campaign configuration document that can be executed in StackAdapt's self-serve UI by the LUXY Ride agency, OR via the GraphQL API when the formal integration is ready.

Also produce a human-readable handoff document (markdown) that the agency can follow step-by-step.

FILES TO CREATE:
- adam/retargeting/integrations/stackadapt_translator.py — sequence → SA config
- adam/retargeting/integrations/stackadapt_models.py — SA-specific data models
- adam/retargeting/integrations/handoff_generator.py — human-readable doc generator
- adam/retargeting/integrations/domain_csv_exporter.py — domain whitelist CSVs
- tests/retargeting/test_stackadapt_translator.py
```

---

<a name="session-10"></a>
## Session 33-10: Claude Argument Generation Engine
**Duration**: 4-5 hours
**Objective**: Build the engine that uses Claude to generate novel, barrier-specific factual arguments for retargeting creative.

**System Prompt for Claude Code**:
```
You are building the Claude Argument Generation Engine — the most powerful
mechanism in INFORMATIV's Therapeutic Retargeting Engine.

CONTEXT: 2024-2025 research (Salvi et al., Nature Human Behaviour) shows
LLM persuasion derives primarily from FACTUAL ARGUMENT QUALITY, not
psychological technique selection. Bozdag (2025) shows multi-turn
coherence across 4+ turns dramatically increases persuasiveness.
Hackenburg & Margetts (2024, PNAS) shows surface personalization produces
NO effect — only deep psychological personalization works.

This engine does something no competitor can do: it takes INFORMATIV's
bilateral edge (27 alignment dimensions), the diagnosed conversion barrier,
the user's 65-dimension psychological profile, and the brand's actual
performance data, then uses Claude to generate a NOVEL factual argument
specifically tailored to resolve that barrier for that psychological profile.

This is NOT template selection. This is reasoned argument generation.

The engine has three modes:
1. FULL GENERATION: Claude generates complete ad copy (headline, body, CTA)
   from scratch. Latency: ~500ms. Used for high-value sequences.
2. ARGUMENT INSERTION: Claude generates a single key factual argument that
   gets inserted into a template. Latency: ~200ms. Used for medium-value.
3. ARGUMENT RANKING: Claude ranks pre-generated arguments by likely
   effectiveness for this specific barrier × profile. Latency: ~100ms.

Multi-turn coherence: The engine maintains a "conversation memory" across
the retargeting sequence. Each subsequent Claude generation receives the
full touch history as context, creating the multi-turn effect that
Bozdag (2025) found dramatically increases persuasiveness.

Real-time personality refinement: Each behavioral response to a touch
provides new personality signal. The engine updates the profile within
the sequence, enabling late-sequence touches to be personalized based
on OBSERVED behavior, not just pre-computed archetypes.

INTEGRATES WITH:
- Enhancement #15 (Copy Generation) — extends with barrier-specific prompting
- Claude Embedded Intelligence Architecture — uses same Claude API patterns
- Enhancement #32 (Edge-Centric) — bilateral edge provides the context
- Enhancement #14 (Brand Intelligence) — brand data provides the facts

FILES TO CREATE:
- adam/retargeting/engines/claude_argument_engine.py — core generation engine
- adam/retargeting/engines/argument_modes.py — full/insertion/ranking modes
- adam/retargeting/engines/conversation_memory.py — multi-turn state
- adam/retargeting/engines/profile_refiner.py — within-sequence personality update
- adam/retargeting/prompts/argument_generation.py — structured Claude prompts
- adam/retargeting/prompts/argument_ranking.py — ranking prompt
- tests/retargeting/test_claude_argument.py
```

---

<a name="session-11"></a>
## Session 33-11: Integration Testing and Validation
**Duration**: 3-4 hours
**Objective**: End-to-end integration tests and psychological validity validation.

**System Prompt for Claude Code**:
```
You are building the integration test suite and validation framework for INFORMATIV's Therapeutic Retargeting Engine.

CONTEXT: The therapeutic retargeting system must be validated at three levels:

1. UNIT TESTS: Each engine component works correctly in isolation.
   Already built in Sessions 33-1 through 33-9.

2. INTEGRATION TESTS: The full diagnostic loop works end-to-end.
   - Given a bilateral edge and behavioral signals →
   - Produces a barrier diagnosis →
   - Selects a mechanism via Thompson Sampling →
   - Builds a therapeutic touch with creative spec →
   - Observes an outcome →
   - Updates priors correctly →
   - Produces a different mechanism on the next iteration

3. PSYCHOLOGICAL VALIDITY TESTS: The system's behavior matches research predictions.
   - Stage-mismatched interventions should perform worse than matched
   - Personality-matched mechanisms should outperform mismatched
   - Reactance should compound with rapid-fire touches
   - Narrative-structured sequences should reduce critical thoughts
   - Implementation intentions should bridge intention-action gap better than reminders

Use the LUXY Ride dataset (3,103 bilateral edges, 5 archetypes) as the test corpus.

FILES TO CREATE:
- tests/retargeting/test_integration.py — full loop tests
- tests/retargeting/test_psychological_validity.py — research-prediction tests
- tests/retargeting/test_luxy_ride_pilot.py — LUXY Ride specific validation
- tests/retargeting/conftest.py — shared fixtures
- adam/retargeting/api.py — FastAPI endpoint implementations
- adam/retargeting/cache.py — Redis caching layer
- adam/retargeting/metrics.py — Prometheus metrics
```

---

# SECTION H: TESTING AND VALIDATION

<a name="section-h1"></a>
## H.1 Psychological Validity Tests

```python
# tests/retargeting/test_psychological_validity.py

"""
These tests validate that the system's behavior matches
the research predictions from the 15 academic domains.

Each test encodes a specific research finding as a testable
system behavior prediction.
"""

class TestTTMStageMatching:
    """Verify that stage-matched interventions outperform mismatched."""
    
    async def test_action_intervention_on_precontemplation_generates_resistance(self):
        """TTM: Action-oriented messages to UNAWARE users should produce negative outcomes."""
        # Given: user in UNAWARE stage
        # When: deploy IMPLEMENTATION_INTENTION (action-stage mechanism)
        # Then: engagement_occurred should be False AND reactance should increase
        pass
    
    async def test_pros_emphasis_2x_cons_in_early_stage(self):
        """Hall & Rossi 2:1 ratio: early messaging emphasizes benefits 2× objections."""
        # Given: user in CURIOUS stage
        # When: build creative spec
        # Then: benefit-to-objection ratio in creative should be >= 2.0
        pass


class TestRuptureRepair:
    """Verify rupture detection and repair dynamics."""
    
    async def test_withdrawal_detected_from_engagement_decay(self):
        """3 consecutive non-engagements should trigger withdrawal rupture."""
        pass
    
    async def test_repair_changes_mechanism(self):
        """Repair strategy should select a DIFFERENT mechanism than the one that caused rupture."""
        pass
    
    async def test_repair_does_not_acknowledge_withdrawal(self):
        """Clinical evidence: explicit acknowledgment ineffective for withdrawal ruptures."""
        pass


class TestReactanceGovernor:
    """Verify Wicklund hydraulic compounding."""
    
    async def test_rapid_touches_compound_reactance(self):
        """Touches <12h apart should produce multiplicative reactance increase."""
        pass
    
    async def test_reactance_exceeds_budget_triggers_suppression(self):
        """When cumulative reactance > budget, sequence should be suppressed."""
        pass


class TestThompsonSampling:
    """Verify Bayesian mechanism selection convergence."""
    
    async def test_mechanism_converges_with_data(self):
        """After 50+ observations, the selected mechanism should stabilize."""
        pass
    
    async def test_personality_modulation_changes_selection(self):
        """High-agreeableness user should get different mechanism than low-agreeableness."""
        pass


class TestNarrativeArc:
    """Verify narrative transportation structure."""
    
    async def test_sequence_follows_5_chapter_arc(self):
        """Touches should progress through intro→complication→rising→resolution→epilogue."""
        pass
    
    async def test_coping_model_selected_for_hesitant_prospects(self):
        """Braaksma: weak learners should get coping models, not mastery."""
        pass
```

<a name="section-h3"></a>
## H.3 Success Metrics

| Metric | Target | Research Basis |
|--------|--------|----------------|
| Per-touch conversion rate increase | Touch N > Touch N-1 | Diagnostic retargeting hypothesis |
| Barrier resolution rate | >30% of diagnosed barriers resolved within 3 touches | Scaffolding g=0.46 × 0.62 calibration |
| Stage advancement rate | >20% of users advance at least one stage | TTM stage-matching (calibrated) |
| Rupture repair success | >20% of detected ruptures successfully repaired | Eubanks d=.62 (wide CI, conservative target) |
| Reactance suppression rate | <10% of sequences suppressed for reactance | Governor effectiveness |
| Mechanism convergence | Thompson Sampling stabilizes within 50 observations | Bayesian learning |
| Personality-matched lift | >12% lift for personality-matched vs. generic | Matz calibrated lift (0.20 × 0.62 production factor) |
| Claude Argument vs Template lift | >25% higher engagement for Claude-generated vs template | Salvi 2024 LLM persuasion advantage |
| Multi-touch coherence effect | Touches 3-5 show higher engagement than sequence-naive touches | Bozdag 2025 multi-turn threshold |
| Sequence completion rate | >60% of sequences reach intended touch count | Engagement quality |
| Overall campaign ROAS improvement | >15% vs. standard retargeting | Conservative: compound bilateral + therapeutic effects with calibrated priors |

**NOTE ON CALIBRATION**: v1.0 of this document targeted >25% ROAS improvement and >20% personality-matched lift based on published effect sizes. Fact-checking revealed substantial publication bias across multiple research domains. The v2.0 targets above use calibrated effect sizes — they are more conservative but more likely to be achieved in production, which matters more for the StackAdapt proof case.

---

*This document serves as the AUTHORITATIVE SOURCE OF TRUTH for Enhancement #33 v2.0. Every Claude Code session should reference this document. The research foundations in Section A are not decorative — they are the engineering specifications that determine system behavior. Each effect size governs a Bayesian prior, using CALIBRATED values (not inflated published values). Each boundary condition governs a system constraint. Each personality interaction governs a mechanism modulation weight.*

*The v2.0 additions from Domain 16 (LLM-Powered Adaptive Persuasion) represent the single largest power upgrade. The original 15 domains tell the system WHAT mechanism to deploy. Domain 16 tells the system HOW to deploy it — by generating novel, barrier-specific factual arguments via Claude rather than selecting from pre-written templates. This is INFORMATIV's deepest moat: bilateral psychological intelligence diagnosing barriers + LLM reasoning generating the arguments to resolve them. No competitor has both.*

*Build it exactly as specified. The psychology IS the engineering. The calibration IS the honesty.*
