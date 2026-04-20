# ADAM HUMAN-MACHINE TEAMING FOUNDATION

**The Second Learning Loop — INFORMATIV's Protocol for Bidirectional Knowledge Exchange**

---

**Purpose.** This document is the intellectual and architectural frame for how INFORMATIV's platform talks to the humans driving it — and how those humans talk back. It sits parallel in status to `ADAM_THEORETICAL_FOUNDATION.md`. The theoretical foundation explains how the platform understands the *end user* (the ad recipient). This document explains how the platform understands the *partner* (the advertiser, the agency planner, the brand operator, and, during pilot, Chris himself). Both are load-bearing. If either is thin, the platform underperforms its theoretical ceiling.

**Load order:** `ADAM_SESSION_RESTORE.md` → `ADAM_CTO_PERSONA.md` → `ADAM_THEORETICAL_FOUNDATION.md` → **THIS FILE** → `CLAUDE.md` → `memory/MEMORY.md`.

**The single question this document answers:** *How does the system and the human transfer knowledge to each other in a way that respects what each is good at, corrects what each is bad at, and generates trustworthy learning on both sides?*

**The single failure mode it guards against:** treating either party's self-reports as ground truth. User self-reports are hypotheses about their own cognition — the same Nisbett & Wilson problem (1977) — and must be tested. Machine confidence scores are hypotheses about the machine's own competence, and must be calibrated. Neither gets to short-circuit the inferential machinery the rest of the platform uses.

---

## 1. Why This Is the Second Learning Loop

ADAM has two learning loops of roughly equal importance.

**Loop A — The analytics loop.** The system observes ad outcomes, updates per-user posteriors, refines mechanism-effectiveness registries, validates bilateral edges, adjusts archetype priors, reweights persuasion techniques, detects decay, and adjudicates inferential claims against statistical thresholds. This is the loop most of the platform's code implements. It is mature and well-instrumented.

**Loop B — The teaming loop.** The system interacts with a human partner who has tacit knowledge the system does not and cannot derive from data alone. The human makes recommendations, overrides, clarifications, and interpretive judgments. The system must elicit those judgments well, calibrate them, test them against outcomes, and feed validated findings back into its models. This is the loop the platform has not yet built. It is the subject of this document.

The two loops are not a hierarchy. They instrument the same underlying reality from different angles. When they agree, confidence compounds. When they disagree, the disagreement is itself diagnostic — usually revealing a hidden confounder neither loop captured on its own. When one loop discovers something the other cannot test (for example: analytics identifies a pattern a human cannot consciously articulate, or a human surfaces a pattern analytics lacks statistical power to detect), the finding gets queued for the other loop to examine. Neither loop trumps the other. Both feed the same Inferential Learning Agent described in §9.

The reason Chris pushes on Loop B now, in pilot phase, is not that he doubts the analytics loop. It is that the teaming loop is the frontier problem of AI as a category — the place where the biggest efficiency gains remain unclaimed — and no competitor in the advertising space has even begun. Solving it during pilot, when Chris is the sole test subject, is the rare opportunity to tune the protocol against an expert user before it has to survive novices.

## 2. The Frontier Problem, Precisely Stated

Humans and machines each possess forms of knowledge the other cannot easily access.

**What humans have that machines struggle with.** Decades of experiential pattern recognition. Gut-level judgment assembled from thousands of situations the human cannot consciously enumerate. Episodic memories that carry emotional and contextual richness no aggregate statistic captures. Cross-domain inference — the ability to see that a situation in advertising resembles a situation in a totally unrelated field, and to transfer a lesson accordingly. Taste. Moral and aesthetic judgment. An internal model of what their client actually wants, versus what their client is saying.

**What the machine has that humans struggle with.** Exhaustive memory of every past observation at the granularity of individual impressions. Statistical discipline — the ability to ignore salient examples and weight evidence by base rates. Counterfactual simulation at scales humans cannot hold in working memory. Uniform treatment of logically equivalent scenarios that human framing makes feel different. Unbiased updating after new data, at least in principle.

**Why transfer fails.**

Humans often fail to articulate what they know. The knowledge is tacit — Polanyi's "we know more than we can tell." They struggle to retrieve it on demand, they compress it into vague generalizations ("young urban professionals respond to ..."), and when pressed, they confabulate — generating plausible-sounding but factually wrong explanations for their own decisions (Nisbett & Wilson 1977). They do not always know what data they have that the machine would benefit from. They are vulnerable to availability effects, framing effects, anchoring, mood contamination, and motivated reasoning. They struggle with fine-grained quantitative estimates. They overfit recent experience. And they often cannot distinguish their own tacit knowledge from confident-sounding guesswork (the Dunning-Kruger problem compounded by domain-crossover).

Machines, in turn, fail at their side of the transfer. They ask questions in formats humans are bad at answering (Likert scales, absolute probability estimates, numeric confidence). They treat the human's explicit claims as ground truth when they should be treating them as hypotheses. They fail to recognize when they are uncertain and to name *what* they are uncertain about in a way that lets the human fill the gap. They fail to request data the human has but didn't think to offer. They fail to discriminate between a human's tacit pattern match (usually reliable) and the human's abstract generalization (usually unreliable). They do not calibrate the human — they do not track how well this specific human forecasts in this specific domain over time.

**The consequence.** The combined human-machine system performs below the sum of its parts. The human feels either overruled or underserved. The machine either trusts too much or too little. Learning plateaus. And the advertising industry, which has not solved any of this, has converged on two dismal equilibria: fully black-box AI (Meta Advantage+, Google Performance Max) or fully manual operation with AI as a decoration. The space between — a genuine partnership — is empty.

**The opportunity.** The platform already has the cognitive substrate to do this well, because everything the analytics loop computes is already structured in a way that can support a proper explanation interface, and because Chris's training in cognitive and social psychology gives us a 40-year body of empirical work to draw on that the rest of the industry is not drawing on.

## 3. Connection to the Theoretical Foundation

The teaming problem is not independent of the mechanism-theory problem. It inherits the same discipline rules.

**Rule 1 (from the foundation). Correlation is not inference.** Applied to Loop B: a user's stated rationale for overriding a recommendation is correlational. It may track the actual cause of their override, or it may be post-hoc confabulation. The platform cannot treat the stated reason as a learning until the override-outcome pair passes a causal test, scoped to the appropriate horizon.

**Rule 2 (from the foundation). Most of cognition is nonconscious.** Applied to Loop B: the human partner does not have full conscious access to their own decision process. The machine must design elicitation to capture tacit knowledge without inviting confabulation. The Fazio-style speeded-response and Greenwald-style implicit paradigms are relevant not as curiosities but as practical tools.

**Rule 3 (from the foundation). The system must embody the mechanism, not approximate it.** Applied to Loop B: the mechanism of human-machine teaming is joint cognition (Hollnagel & Woods 2005, Hutchins 1995) with calibrated trust (Lee & See 2004) under mixed initiative (Horvitz 1999). The implementation must be these frameworks, not window dressing that cites them.

**Rule 4 (from the foundation). Chris has studied this material at depth; do not explain it back to him.** Applied here: Bargh's automaticity research, Pinker's dual-mechanism theory, Ridley's dynamic competition motif, primary metaphor theory — these are not references, they are the working intellectual apparatus. The machine must be built to exploit them, including in the dialog surface.

**Rule 5 (the new rule this document adds).** *User self-reports are hypotheses, not learnings.* This applies to every statement the human makes: preferences, confidence, explanations, recollections, predictions, override rationales. Each enters the system as a `Claim` node with `status: hypothesis`. It is promoted to `status: validated` only after outcome instrumentation and causal adjudication. The same inferential discipline the platform applies to ad signals applies to user speech.

## 4. Cognitive-Science Foundations for Elicitation

The rest of the document depends on a small set of findings from cognitive and social psychology. They are not the platform's contribution — they are the canon we're building on. Condensed here so the architecture sections make sense without a detour.

### 4.1 The tacit-explicit asymmetry

Polanyi's observation that humans know more than they can tell is not a metaphor. The bulk of domain expertise is stored as perceptual-motor patterns, episodic fragments, and emotional associations that are not linguistically encoded. Nonaka & Takeuchi's SECI model decomposes knowledge conversion into four types — socialization (tacit → tacit), externalization (tacit → explicit), combination (explicit → explicit), and internalization (explicit → tacit). Externalization is the hardest, and it is exactly the move elicitation must accomplish. Nisbett & Wilson (1977) established, in a series of now-classic experiments, that people confidently report causes of their own behavior that can be shown to be wrong — not because they are lying, but because they are confabulating plausible narratives. The implication for platform design: when we ask a human *why* they did something, we are often asking them to generate fiction.

### 4.2 Dual-process theories

The convergent view (Evans & Stanovich 2013) is that human cognition runs two kinds of process. Type 1 is autonomous, fast, working-memory-independent, and usually right in familiar domains. Type 2 is deliberative, slow, working-memory-dependent, and responsible for explicit reasoning. The default-interventionist model holds that Type 1 runs by default and Type 2 intervenes only when the problem is hard enough to warrant it — and the human has the motivation and available working memory to engage.

This has direct implications for elicitation. If we want tacit pattern-matching knowledge from an expert, we want Type 1 to answer. If we want explicit tradeoff reasoning, we want Type 2. The interface should be designed to select which one responds. Time pressure and concurrent cognitive load (digit-span tasks, dot-pattern memory) force Type 1 by knocking out Type 2. Leisurely text prompts invite Type 2, which in tacit domains is exactly where confabulation lives.

Epstein's Cognitive-Experiential Self-Theory complicates the picture: individuals differ in their preferred system (measurable via the Rational-Experiential Inventory), so the same elicitation format pulls intuition from one user and deliberation from another. Per-user calibration of the protocol itself becomes a first-class problem.

Bargh's auto-motive model (1990, Bargh et al. 2001 "The Automated Will") extends the dual-process frame from attitudes to goals. Goals repeatedly activated in a situational context become automatically activated by that context without conscious intent. The downstream behavior is indistinguishable from a consciously pursued goal. This is why nonconscious priming of an audience's goals matters in the ad placement itself — and it is also why probing an expert for their tacit goals around a brand, via priming-style tasks, can recover patterns the expert cannot articulate directly.

### 4.3 The heuristics and biases catalog

Kahneman & Tversky (1974 and subsequent) mapped the systematic errors that arise when humans substitute a simple judgment for a harder one. Each heuristic is a potential elicitation contaminant the platform must design around.

*Anchoring.* The 8!-estimation finding: ascending order (1×2×3×…×8) produces a median estimate of 512; descending (8×7×6×…×1) produces 2250. Numeric prompts anchor. The countermeasure with empirical support is "consider the opposite": force the user to generate reasons an anchor could be wrong before eliciting the estimate (Nagtegaal 2020 replication). Warnings alone do not work.

*Availability.* Ease of retrieval drives judgment more than content of retrieval (Schwarz 1991). Asking a user to "name twelve examples" produces a *worse* rating than "name six" because twelve feels hard. Any retrospective report about how customers behaved is contaminated by what comes to mind first.

*Representativeness.* Users answer "how likely is X" by answering "how similar is X to my prototype," ignoring base rates. Predictive elicitations are especially vulnerable.

*Framing and loss aversion.* Prospect theory (Kahneman & Tversky 1979) establishes that gains and losses are valued asymmetrically, roughly 2:1. "What do you want to avoid" elicits different priorities from "what do you want to achieve," and both are real regulatory-focus signals, not noise. The platform should run elicitations in *both* frames and treat the delta as data.

*Hindsight bias (Fischhoff 1975).* After outcomes, people overestimate predictability. The countermeasure is time-stamping predictions and surfacing the original estimate before asking retrospectively.

*Confirmation bias.* Users ask "can I believe this?" of confirming evidence and "must I believe this?" of disconfirming. Again, consider-the-opposite protocols help.

*Mood as information (Schwarz & Clore 1983).* The sunny-day / rainy-day study: life-satisfaction ratings tracked weather, but the effect disappeared when subjects were cued to attribute their mood to the weather. Implication: any elicited importance / satisfaction / preference rating is contaminated by ambient mood unless we surface it.

*Morewedge's debiasing work (2015, 2020).* Interactive debiasing training — video plus game plus feedback — produces effects that transfer to the field and persist. Pure lectures don't. If we onboard humans into a calibration habit, the investment pays.

### 4.4 What humans do well (the structure we exploit)

Not everything about human judgment is broken. The following are robust capabilities elicitation should build on.

*Paired comparison over absolute judgment.* Thurstone's Law of Comparative Judgment (1927) established that humans can reliably discriminate between two stimuli even when they cannot place either on a numerical scale. The Bradley-Terry model (1952) gives a probabilistic formalization: P(A beats B) equals the ratio of latent strengths. Modern machine learning has quietly discovered this — reinforcement learning from human feedback (RLHF) and direct preference optimization (DPO) both sit on top of Bradley-Terry mathematics. The binary forced-choice task is the cleanest way to extract preference data from a human. Likert scales, by comparison, suffer central-tendency bias, extreme-response bias, acquiescence bias, social-desirability bias, and scale-use heterogeneity (documented across decades of survey-methodology research). Chris's own empirical practice has converged on the same finding.

*Signal detection theory (Tanner & Swets 1954).* Provides the formalism for why forced choice is cleaner: it separates sensitivity (d') from response bias (β or c). A Likert response conflates both. A two-alternative forced choice with balanced base rates measures sensitivity alone. We can recover whether the user genuinely discriminates or is noise.

*Recognition over recall.* Recognition tasks ("which of these three descriptions matches your best customer?") produce more accurate retrieval than recall tasks ("describe your best customer"). Because recognition traces partial matches and cued retrieval, while recall requires full reconstruction.

*Episodic over semantic.* Asking an expert to recall a specific instance ("tell me about the best campaign you ever ran and why") yields more accurate tacit knowledge than asking for a generalization ("what makes campaigns work"). Episodic memory is richer and less vulnerable to post-hoc theorizing. Story prompts are high-bandwidth elicitation.

*Counter-example probes.* Asking "when does this NOT work?" recovers implicit boundary conditions an expert has never made explicit. It also reduces confirmation bias in the response.

*Fast intuitive answers under time pressure.* Where the judgment lives in Type 1, forced-speed responses are more accurate than deliberate ones. This is the Fazio-style priming paradigm generalized. In applied contexts, a visible countdown plus a binary choice will often produce better data than a long-form question with no time limit.

### 4.5 Calibration training

Tetlock's Good Judgment Project (2011–2015) demonstrated that human forecasting accuracy is trainable. The Mellers et al. 2014 protocol — a roughly forty-minute training covering reference-class forecasting, inside/outside view, overconfidence countermeasures, and averaging of multiple estimates — produced a consistent ~6% improvement in standardized Brier score over controls, compounded when combined with small-group aggregation and identification of top individual forecasters.

The Brier score (mean squared error between forecast probability and outcome) is a proper scoring rule: honest reporting is optimal. It decomposes into calibration + resolution + uncertainty. Superforecasters score around 0.14 on binary geopolitical questions, with measurable discrimination at 1% granularity — their accuracy *drops* when forecasts are rounded to nearest 0.05, meaning they genuinely perceive differences that fine.

Calibration does *not* transfer cleanly across domains (Le 2026 decomposition of prediction-market data across weather, sports, politics, and technology). A user calibrated on creative-performance forecasts is not automatically calibrated on audience-sizing forecasts. Per-user per-domain calibration tracking is required. This becomes the `CalibrationJournal` component specified in §9.

For range elicitation, two specific protocols dominate. SPIES (Haran, Moore & Morewedge 2010) replaces "give me a 90% confidence interval" with "distribute 100 probability points across these bins." Traditional 90% CIs capture the true value ~30% of the time; SPIES intervals capture ~74%. And Speirs-Bridge et al. (2010) establish the four-point protocol: ask for lowest plausible value, highest plausible value, best estimate, and *self-reported confidence that the true value is in the stated range*. The four-point structure produces better-calibrated intervals than direct CI elicitation.

## 5. The Field of Human-Machine Teaming

Human-machine teaming (HMT) is an active research domain with a forty-year history and almost zero adoption in advertising technology. The platform should adopt its canonical frameworks directly.

*Cognitive Systems Engineering (Hollnagel & Woods 2005).* The move: stop treating human and machine as separate entities that interact, and treat the *joint cognitive system* as the unit of analysis. Cognition is distributed across agents and artifacts; capabilities are properties of the coupling. Top-down functional analysis, not bottom-up information-processing.

*Distributed Cognition (Hutchins 1995).* Parallel development from cognitive anthropology. Three distributions: across a social group, across internal/external structure (the cockpit, the ship's bridge, the ad operator's dashboard), and across time. Navigation exists in the ship's navigation system, not in any one crew member's head. Applied to us: ad strategy exists in the Chris-plus-ADAM system, not in either alone.

*Mixed-Initiative Interaction (Horvitz 1999).* The foundational CHI paper for how an AI agent should share initiative with a user. Twelve principles: consider uncertainty about user goals; weigh expected utility of autonomous action against asking; use dialog to resolve uncertainty; provide efficient collaboration mechanisms; employ socially appropriate behaviors; maintain working memory of recent interactions; continue to learn by observing. The Lookout scheduling prototype was the exemplar. These principles become a design checklist for every interaction surface we build.

*Calibrated trust (Lee & See 2004, "Trust in Automation: Designing for Appropriate Reliance").* The canonical framework. Calibrated trust equals the correspondence between a user's trust and the automation's actual capabilities. Overtrust produces misuse; distrust produces disuse. Three factors drive trust formation: Performance (does it work?), Process (how does it work?), and Purpose (what is it for?). Trust is dynamic and shaped by context, affect, and individual differences. Calibration should be measured — accept/override ratios tracked against actual accuracy per decision class — and flagged when systematic misuse or disuse appears.

*Interactive machine learning (Amershi et al. 2014, Amershi et al. 2019 Guidelines for Human-AI Interaction).* Power to the People established that users resent being treated as oracles; frustration and interruption are first-class design variables. The 18 Guidelines for Human-AI Interaction (CHI 2019) are the baseline spec for user-facing AI components: set expectations, make clear what the system can do, match relevant social norms, mitigate social biases, support efficient correction, learn from user behavior, update cautiously, notify users about changes, encourage granular feedback, convey the consequences of user actions, provide global controls, support efficient dismissal, support efficient invocation, scope services when in doubt, make clear why the system did what it did, remember recent interactions, support efficient invocation of a human.

*DARPA XAI (2017–2021).* Produced techniques for explanation generation but mixed results on actual trust calibration. Explanations help build mental models; they do not automatically calibrate trust. The successor programs (Competency-Aware ML; ASSIST / Perceptually-enabled Task Guidance) shifted toward systems that communicate *what they know they can and can't do*, not prediction+confidence alone. This is the "self-uncertainty decomposition" move §7 specifies.

*Recent HMT reviews (2022–2025).* Consensus capabilities: observability (what is the machine doing?), predictability (what will it do next?), directability (can the human steer it?), shared mental models (bidirectional — the human models the AI, and the AI models the human), common ground, coordination protocols.

*Advertising-industry adoption: effectively zero.* There is no published work applying calibrated-trust frameworks, mixed-initiative principles, or joint-cognitive-system analysis to DSPs, attribution tools, or creative-optimization systems. This is a real gap, not hidden prior art. The platform has the opportunity to be the first implementation, and the research literature is publishable.

## 6. Chris Nocera's Elicitation Principles (Empirically Derived)

Three principles are already established in Chris's own research practice. They will anchor the platform's elicitation toolkit. Recording them here so future sessions treat them as load-bearing.

**Principle 1 — Binary forced-choice over Likert, always.** Likert scales presuppose a fine-grained numeric judgment humans cannot reliably produce. Binary forced-choice ("A or B?") respects the discrimination capability humans actually have. Paired-comparison data can be aggregated into Thurstonian or Bradley-Terry scales server-side to recover the latent continuum; the user never has to produce a number. Every preference elicitation in the platform defaults to binary. Ranked or k-alternative formats are acceptable when necessary; Likert is not.

**Principle 2 — Time pressure forces honest answers.** A visible countdown and a short response window (2–5 seconds for a paired choice) pushes the user into Type 1 responding. The resulting answers are less contaminated by conscious deliberation, social desirability, or post-hoc rationalization. Response latency itself is a signal: fast responses indicate tacit/confident; slow responses indicate deliberation or uncertainty. Latency should be logged alongside the response.

**Principle 3 — Bias and mood are first-class contaminants.** Every elicitation must account for the possibility that the user's current state — mood, recent salient events, priming by the surrounding interface, anchoring by earlier questions — is contaminating the answer. The platform should (a) surface mood state at session start via a fast two-alternative choice, (b) randomize the order of comparison pairs to suppress anchoring, (c) run key elicitations in both gain and loss frames and treat the delta as diagnostic, and (d) flag high-stakes claims for re-elicitation at a later session to detect state-dependent inconsistency.

These three — Chris's empirical practice — combine with the field's literature (§4) to produce the full toolkit specified in §8.

## 7. The Machine's Obligations

Before the architecture, name what the machine must be capable of. Six obligations. Each must be implementable and instrumentable.

**7.1 Self-uncertainty decomposition.** The machine must know, at every recommendation moment, what it is confident about and what it is not — at a granular level, not as a scalar. A confidence percentage is not adequate. The required output is structured:

- *Confident:* specific sub-decisions the machine has strong evidence for (cite the edges, the posterior mass, the atoms that produced agreement).
- *Uncertain:* specific sub-decisions with insufficient evidence (name the missing signal, the small sample, the category we lack data in).
- *Possibly wrong:* specific sub-decisions where evidence exists but suggests the prediction may be off (identify the conflicting signal, the base-rate violation, the edge with low but non-trivial disagreement).

This is not new model work. The bilateral cascade, atom activations, and evidence counts already produce the raw material. Self-uncertainty decomposition is a *surfacing* of what is already computed, structured as the competency-aware output that DARPA's 2020s programs were pushing toward.

**7.2 Elicitation-mode selection.** The machine must choose the *format* of a question based on the kind of knowledge it needs. Ten formats are specified in §8. The machine must know, for each unfilled slot in the platform's knowledge graph, which format is appropriate. A rule-based selector is sufficient for v0.1; a learned selector comes later.

**7.3 Data-ask discrimination.** Often the missing information is not in the human's head — it is in their email, CRM, support tool, or call recordings. The machine must be able to distinguish the questions whose answer requires a human judgment from the questions whose answer requires an artifact, and request the artifact rather than the judgment. Every uncertainty in the machine should trigger a check: is there a data source that would reduce this uncertainty more reliably than asking?

**7.4 Tacit-vs-guess discrimination.** When a human asserts something confidently, the machine must discriminate between tacit knowledge (reliable) and confident guess (unreliable). Three v0.1 signals suffice: (a) recallability — "can you remember a specific instance where this was true?" — with fluent episodic recall weighting tacit knowledge up and abstract restatement weighting it down; (b) consistency across re-elicitations in different frames; (c) agreement with analytics-loop signals. A confident assertion that a human cannot recall instances of, that changes when re-framed, and that disagrees with the analytics signal, enters the system as a low-weight hypothesis.

**7.5 Per-user calibration tracking.** Every confidence-bearing statement the user makes — "I'm sure this will work," "I think CPA will be around $40," "I doubt this audience cares about price" — must be logged with timestamp, stated confidence, machine prior, and subsequently with the outcome. A per-user-per-domain calibration curve is built over time. The user's confidence is re-weighted at the machine's end by the user's empirical calibration history. Optionally and ideally: the user sees their own calibration, Brier score, and trend — surfaced as a live metric they can improve. Tetlock's research says calibration training works; the platform's product-surface can be the training.

**7.6 Mood and bias contamination detection.** The platform must instrument:
- *Session-start mood check:* a two-alternative choice that indexes affective state ("which of these two images feels more like your current state?"). This mood index is covariate-adjusted out of subsequent elicitations.
- *Pair-order randomization:* to suppress anchoring from earlier items in the session.
- *Dual-frame elicitation:* key questions asked in gain and loss frames, with the delta logged.
- *Cross-session consistency:* high-stakes claims re-elicited at a later session, inconsistency flagged.
- *Consider-the-opposite protocols:* before committing to a high-stakes elicited claim, the user is asked to generate one reason the claim could be wrong.

## 8. The Elicitation Toolkit

Ten question formats. Each has a specification: when to use, how to use, what to log, how to score.

**8.1 ForcedPair (binary paired comparison, leisurely).**
Two alternatives, user picks one. No time limit. Good for any preference judgment where contamination risk is moderate.
Log: `user_id`, `pair_id`, `item_a`, `item_b`, `choice`, `latency_ms`, `timestamp`.
Score: aggregate into Bradley-Terry strengths over many pairs.

**8.2 TimedPair (binary paired comparison, speeded).**
Same as ForcedPair but with a visible countdown (default 3s). Forces Type 1 response. Good for tacit knowledge, intuitive preferences, implicit attitudes. Use for anything where System 2 deliberation would invite confabulation.
Log: all of the above plus whether the deadline was hit.
Score: same as ForcedPair, with a latency-based confidence weight (fast choices weighted up).

**8.3 kAFC (k-alternative forced choice).**
User picks one from k options (typically 3–5). Useful when binary is too coarse — e.g., "which of these four customer descriptions best matches your best-performing segment?"
Log: position of options (randomized), choice, latency.
Score: multinomial; convert to pairwise via tournament decomposition if needed.

**8.4 RankOrder.**
User orders k items. More data per trial than kAFC but harder cognitively. Use sparingly.
Log: order, latency per pair swap if the UI supports it.
Score: Plackett-Luce or Borda count.

**8.5 StoryPrompt (episodic recall).**
Free-text prompt anchored in a concrete instance ("tell me about the best campaign you ever ran and exactly why it worked"). Extracts episodic detail that subsequent abstract-generalization prompts will miss.
Log: text, time to first keystroke, total time, keystroke bursts (proxy for fluency).
Score: LLM-parsed for patterns, constructs, emotional tone, temporal specificity. Store structured parse alongside raw text.

**8.6 CounterExamplePrompt.**
"When does this not work?" or "Describe a situation where you would *not* apply this." Reduces confirmation bias and extracts implicit boundary conditions.
Log: same as StoryPrompt.
Score: same as StoryPrompt, with extracted conditions indexed as candidate scope-restrictors on the user's prior claim.

**8.7 RecallabilityProbe.**
Immediately after a confident claim, ask: "Can you think of a specific instance where you saw this happen?" Then score the response on recall fluency.
Log: prompt, whether the user produced an instance, fluency (time-to-answer, detail level).
Score: tacit-knowledge weight — fluent recall → high; hesitation then abstract restatement → medium; no recall → low (treat prior claim as low-weight hypothesis).

**8.8 ScenarioVignette.**
A concrete situation is described in enough detail that the user can pattern-match ("Imagine you're three weeks in and CPA jumped 40%. What happened?"). Extracts tacit decision-rules.
Log: vignette text, response (often free-text or kAFC), time.
Score: depends on variant.

**8.9 SPIES (probability-bin allocation).**
For any range elicitation, present pre-defined bins covering the outcome space and ask the user to distribute 100 probability points across them. Combine bins to produce any interval. Empirically produces dramatically better-calibrated intervals than direct CI elicitation.
Log: bin definitions, allocation, timestamp.
Score: convert to distribution (histogram → density); compute calibration against eventual outcome when observed.

**8.10 FourPointEstimate (Speirs-Bridge).**
For quantity estimates, ask four things in order: lowest plausible, highest plausible, best estimate, self-reported confidence that the true value is in the stated range. Out-performs direct CI elicitation.
Log: all four values.
Score: interval + point; track confidence calibration separately from point-estimate calibration.

**Selection logic.** The mode selector uses a simple rule-set in v0.1:

| Knowledge target | Recommended mode |
|---|---|
| Tacit preference, contamination risk low | ForcedPair |
| Tacit preference, contamination risk high (System 2 would confabulate) | TimedPair |
| Choice among many candidates | kAFC |
| Episodic detail from an expert | StoryPrompt |
| Boundary conditions / implicit rules | CounterExamplePrompt |
| Confidence check on a claim | RecallabilityProbe |
| Decision-rule extraction | ScenarioVignette |
| Quantity range | SPIES (preferred) or FourPointEstimate |
| Ordinal importance | RankOrder |
| Mood/state probe | TimedPair with affective stimuli |

Mode choice is logged alongside the response so later analysis can evaluate which mode produced the best-calibrated data for this user in this domain. Mode selection itself becomes a learning target.

## 9. The Two-Loop Architecture

Both learning loops feed the same Inferential Learning Agent (already built in the platform, 6-level OBSERVE → VALIDATE → HYPOTHESIZE → DESIGN → APPLY cascade). The agent does not care whether the hypothesis came from analytics or from a human. It runs the same instrumentation, the same causal-inference thresholds, the same scope-determination logic (Task 27's DerSimonian-Laird I²), and the same decay monitoring (Task 32).

### 9.1 Loop A — Analytics

Sketched only because it is mature and documented elsewhere. Task 23 (DSP performance pull) → Task 24 (normalization) → Task 25 (hypothesis testing) → Task 26 (bilateral analysis) → Task 27 (scope determination) → Task 28 (directive generation) → Task 29 (coherence validation) → Task 30 (execution) → Task 31 (tier reporting) → Task 32 (rollback monitor). Thompson sampling, hierarchical priors, per-user posteriors, bilateral edge updates. Existing.

### 9.2 Loop B — Teaming

New. Schema:

```
(User) -[:ASSERTED]-> (Claim {
    text, elicitation_mode, stated_confidence, latency_ms,
    frame, status: "hypothesis", timestamp
})
(Claim) -[:TESTED_AGAINST]-> (Outcome {
    observation, horizon, timestamp
})
(Claim) -[:HAS_STATUS]-> (LearningStatus {
    current: captured | instrumented | testing |
             validated_user_right | validated_system_right |
             indeterminate | retired
})
(User) -[:CALIBRATION_IN]-> (Domain) -[:SCORE]-> Brier
(User) -[:DEVIATED_FROM]-> (Recommendation {
    system_choice, user_choice, system_counterfactual,
    stated_rationale, outcome_observed, causal_adjudication
})
```

Every user utterance — preference choice, override rationale, forecast, claim — enters as a `Claim` with `status: hypothesis`. It never auto-promotes to learning. Promotion requires:

1. **Instrumentation.** The claim is attached to one or more observable outcomes over a defined horizon. If the claim is untestable (pure preference with no downstream outcome), it stays on the user's profile as an idiosyncratic preference and does not generalize.

2. **Horizon completion.** Different decision classes have different expected time-to-causal-signal. Bid nudges: hours. Creative rotation: days to weeks. Archetype selection: weeks to months. Brand-positioning shifts: months to quarters. The system must not adjudicate before the horizon — premature adjudication produces false conclusions. Between elicitation and adjudication, the claim's `status` is `testing`.

3. **Causal adjudication.** When the horizon passes, the Inferential Learning Agent runs the causal test. The design-effect-adjusted statistical machinery from Enhancement #36 (MixedEffectsEstimator, ICC-aware, repeated-measures-capable) is the right apparatus. Three outcomes:
   - *validated_user_right:* user-asserted claim / deviation caused better outcomes with statistical and mechanistic support. System flags itself wrong, investigates what it missed, updates priors at the scope the evidence supports.
   - *validated_system_right:* user-asserted claim / deviation caused worse outcomes with statistical support. Build a defensive warning in the Why Library (§9.3) for similar future situations, keyed to the user's cognitive-bias pattern.
   - *indeterminate:* no causal signal at the appropriate horizon. Stay as idiosyncratic preference; do not generalize.

4. **Continuous re-testing.** Validated learnings are not frozen. Task 32 (rollback monitor) watches validated claims for decay. New observations update the posterior. A learning valid in Q2 may retire in Q4 if the market shifts.

### 9.3 Cross-pollination

The two loops interact:

*Agreement.* When the analytics loop independently validates a claim the teaming loop already confirmed (or vice versa), confidence compounds faster than either loop would allow alone. The joint evidence is worth more than the sum.

*Disagreement.* When the loops disagree, the disagreement itself is the signal. The platform flags for deeper investigation and does not update either side yet. Disagreements usually resolve to a hidden confounder. Sometimes the analytics was seeing a selection artifact; sometimes the human was seeing what the data couldn't yet show.

*Pre-emption.* When the analytics loop discovers a pattern the human has not (yet) surfaced — for example, "users in category C tend to over-index on creative freshness at the expense of sustained message consistency" — the system uses that as *defensive rationale proactively* when the human is about to deviate in the predicted direction. The recommendation rationale surfaces it before the deviation happens: "I'm recommending message consistency over creative refresh here. Our data suggests humans often want to refresh creative at this point; here's what we've seen when they do."

*Escalation.* When the teaming loop discovers a pattern the analytics loop has not tested, the pattern is queued for analytical testing. Human-source hypotheses become platform-level experimental candidates if they reach a critical mass.

### 9.4 The Why Library

A growing, structured library of validated "humans-tend-to-lean-this-way-when-X-and-it-tends-to-fail" findings. Each entry contains:

- Trigger pattern (what situation evokes the bias).
- Bias class (anchoring, availability, recency, familiarity, anecdotal-weighting, status-quo, confirmation, etc.).
- Evidence strength (Brier-weighted, corroborated-across-users count).
- Scope (individual-user, brand-specific, category-specific, platform-wide).
- Canonical countermeasure (the system-side intervention that worked).

Surfaced at decision moments as defensive reasoning:
> "You're considering reallocating budget toward the creative that performed best in the last 48 hours. Users in your situation often do this. In our data, short-window creative-reallocation decisions correlate with a 14% average CPA degradation over the following two weeks. The underlying pattern appears to be recency-weighted variance being misread as signal. Want to see the 14-day running windows instead?"

This is also testable. The *warning itself* has a posterior: sometimes the user would have deviated and done fine. The warning was overcautious. Track that too. The library is a learning artifact of the platform.

### 9.5 Multi-horizon adjudication

Some deviations produce short-horizon wins that hide long-horizon damage. Brand-equity effects, fatigue effects, audience depletion, reactance accumulation. The system must not flip on short-horizon wins if its long-horizon rationale is still intact.

Every recommendation carries an explicit horizon claim: "I expect this to improve CPA by 12% over 14 days" or "I expect this to improve LTV by 8% over 90 days." When the user overrides and an outcome is observed before the horizon, the adjudication flags "too early" rather than proclaiming validation. The `LearningStatus` includes horizon-aware gating.

When short-horizon and long-horizon signals disagree, the system surfaces both: "Short-horizon CPA improved 6% after your override. Long-horizon brand-equity proxy (return-visit rate at 60 days) is running 3% below where we'd expect. Likely interpretation: you won the immediate campaign but accumulated decay in the audience. Worth watching."

## 10. The Interaction Protocol Is Itself a Learning System

The central architectural commitment of this document. The interaction protocol — which questions to ask, in which format, at which moment, with which framing — is not designed once and deployed. It is built as a learning system from the start.

Chris is user zero. Every exchange populates training data. After the first pilot we will have (question, elicitation_mode, user_response, user_latency, user_recallability, subsequent_outcome) tuples. These let us evaluate which modes produced the best-calibrated data for this user in this domain. In later pilots, the protocol adapts — starting from what we learned on Chris, updating for each new user's REI profile, calibration history, and domain expertise.

A few implications:

*The system is allowed to be clumsy at first.* Version 0.1 will misuse elicitation modes, ask questions in the wrong frame, miss opportunities to probe for tacit knowledge, and occasionally frustrate the user. Those failures are data.

*The user is a partner in protocol refinement, not just a subject.* Chris's reflective commentary on what the interface does badly is first-class data, logged alongside the elicitation responses. "That question was dumb because it was asking me to articulate something I can't articulate" is the most valuable kind of feedback for the protocol-learning loop.

*Per-user protocol adaptation is a first-class goal.* Different users will need different elicitation cadences, different ratios of story prompts to forced pairs, different tolerance for time pressure, different trust curves. The system learns each user's shape.

*Protocol failures do not contaminate content learnings.* A badly-framed question producing a noisy response should be recognized as such and not promoted to learning. The mode-selection and elicitation-quality meta-analytics must filter content learnings by protocol confidence.

## 11. System Architecture (Concrete)

Seven components. Each maps to a build unit.

**11.1 The Uncertainty Panel.**
For every AI-generated recommendation, a rendered view with three columns: Confident / Uncertain / Possibly Wrong, each populated from existing evidence counts, atom confidences, and bilateral-cascade outputs. No new model work. Structured surfacing. Mandatory on every recommendation touch-point.

**11.2 The Dialogue Ledger.**
Neo4j subgraph capturing every user-system interaction as typed nodes (see §9.2 schema). Indexed by user, timestamp, claim, and outcome. Backing the learning loop.

**11.3 The Elicitation Toolkit.**
Ten format generators (§8). Each takes a context ("we need to elicit X from user U about brand B in phase P") and returns a rendered question. Each logs to the Dialogue Ledger with mode tag.

**11.4 The Calibration Journal.**
Per-user, per-domain calibration curve. Brier score updated with each validated claim. Surfaced in the user interface as a live metric. Passive in v0.1; interactive and training-capable in v0.2+.

**11.5 The Deviation-Hypothesis Lifecycle.**
Every deviation event creates a `HumanDeviation` node linked to the original recommendation's counterfactual. Instrumentation starts. Horizon expiry triggers adjudication. Three-way branch (§9.2). Results feed the Why Library and the analytics-side learning.

**11.6 The Why Library.**
Structured collection of bias-pattern / trigger / countermeasure triples. Queried at recommendation time to produce pre-emptive defensive reasoning.

**11.7 The Protocol Meta-Learner.**
Tracks mode-selection quality, elicitation calibration, and per-user protocol adaptation. Slow-running; nightly at first. Produces mode-selection policy updates and user-specific protocol parameters.

## 12. The v0.1 Starting Rig

The smallest thing that makes the architecture real. Build order:

1. **Uncertainty Panel (v0.1).** Surface the existing bilateral-cascade + atom-confidence + evidence-count output as structured Confident/Uncertain/Possibly-Wrong bullets alongside every recommendation rendered for Chris during pilot. No new model work; purely a rendering pass.

2. **Dialogue Ledger schema in Neo4j.** Add the node/relationship types from §9.2. Start logging every user interaction, even before the UI is rich. The log is the asset.

3. **Elicitation Toolkit (four generators).** ForcedPair, TimedPair, StoryPrompt, RecallabilityProbe. These four cover ~80% of the data we need for a first pilot and they are the simplest to implement. Add counter-example and SPIES in v0.2.

4. **Session-start mood probe.** Two-alternative timed choice on affective imagery. Index mood. Covariate-adjust subsequent elicitations.

5. **Per-claim instrumentation plumbing.** Every claim in the ledger gets attached to an outcome horizon and a testable target. Without this, nothing validates; the loop never closes.

6. **Chris as user zero.** Run the first full pilot with Chris as the operator, ADAM as the partner, the elicitation toolkit in play, the uncertainty panel visible, the dialogue ledger capturing everything. After each major decision, a 2-minute reflective-commentary affordance: "was this exchange useful? what was missing?" That feedback populates the meta-learner's training data.

Success criteria for v0.1 (not marketing metrics — learning-loop metrics):
- ≥90% of AI recommendations rendered with a populated Uncertainty Panel.
- ≥95% of user-machine exchanges captured as structured ledger entries.
- A first pass at per-user calibration for Chris across at least three decision classes.
- At least five claims instrumented with outcome horizons; at least two of those have passed the horizon and been adjudicated.
- A first entry in the Why Library based on either validated-user-right or validated-system-right learning.
- A first protocol-meta-learner finding — for example, "Chris responds fastest and most consistently on TimedPair, slower and more variably on StoryPrompt except when the prompt anchors on a specific campaign" — that can steer v0.2 mode selection.

## 13. Phased Path to Self-Service

Concretized from the earlier synthesis.

*Phase A — Co-Pilot MVP (6–8 weeks from start).* v0.1 rig operational. Chris as user. First one advertiser (likely LUXY) runs a full campaign through the Discovery → Plan → Execution flow with Chris as approver. Every decision is logged. Uncertainty Panel on every recommendation. Elicitation toolkit driving the Q&A dance. Dialogue Ledger backing the learning.

*Phase B — Delegated Execution (8–12 weeks).* Auto-push to StackAdapt; five autopilot modes (§7.2 of the earlier synthesis); audit-trail UI; Task 33 Decay Adjudicator online; first cross-advertiser pattern in the Why Library. 3–5 advertisers running. Chris intervenes only on ambiguity flags.

*Phase C — Multi-Tenant Platform (12–20 weeks).* Partner / Advertiser / Workspace role hierarchy (DV360 model + StackAdapt client-admin self-provisioning). Agency seat management. Phases 5–8 of Discovery instrumented. Trust-curve graduation logic. Human-system agreement posteriors as a first-class signal. First agency self-onboards an advertiser end-to-end without Chris touching.

*Phase D — Self-Service at Scale (6+ months).* Public signup with gated approval. Persona-adaptive Discovery. Cross-brand pattern learning with privacy-preserving scoping. API access. Calibration training embedded in onboarding.

## 14. Discipline Rules (Added to the Foundation)

These extend the discipline rules in `ADAM_THEORETICAL_FOUNDATION.md`.

**Rule 12. User self-reports are hypotheses, not learnings.** No user-asserted claim auto-promotes to a system-level update. Every claim requires instrumentation, horizon completion, and causal adjudication. Apply the same standard the analytics loop uses for ad-outcome signals.

**Rule 13. The interaction protocol is a learning system, not a designed system.** The platform does not settle on "the right way to talk to humans." It builds the machinery that learns how to talk to each human in each domain, and treats every interaction as training data. Protocol-level adaptation is first-class.

**Rule 14. Binary over Likert. Timed over leisurely.** For any preference or intuitive judgment, default to binary forced-choice. For any tacit domain, default to time-pressured responding. Likert is an exception requiring justification, not a default.

**Rule 15. Explanation is signal-level, not confidence-level.** A recommendation's rationale names the edges, atoms, and evidence counts that produced it. A confidence percentage is not a rationale. Users who see signal-level reasoning build accurate mental models; users who see only scores do not.

**Rule 16. Affordance scales with blast radius.** Reversible decisions deserve lightweight surfaces (ghost text, inline chips). Structural decisions deserve diff views with plan-before-patch. Irreversible decisions deserve modal confirmation with one-click rollback / checkpoint. Mismatch between affordance and blast radius is the source of most over-trust and most distrust.

**Rule 17. Graduation is explicit and opt-in.** Autopilot modes are offered to users after observed evidence that the pair (this user, this decision class) has stabilized. Graduation is never silent. Downgrade is one click, always. Auto-mode *tightens* safety rules rather than loosening them.

**Rule 18. Calibrated trust is measured, not assumed.** Every user-system pair has a live calibration profile: accept/override ratio against actual accuracy, per decision class, per domain. Systematic misuse (overtrust) and systematic disuse (distrust) are flagged as anomalies, not ignored as preference.

**Rule 19. Mood, bias, and temporal state are contaminants to be instrumented.** Elicitations must account for ambient state. Session-start mood probes, randomized pair orders, dual-frame elicitations for high-stakes claims, and cross-session consistency checks are standard, not optional.

**Rule 20. Protocol failures do not contaminate content learnings.** A badly-elicited response must be recognized and excluded from learning updates, even when the user answered confidently. The meta-learner (§11.7) is the filter.

**Rule 21. Humans and machines are one joint cognitive system.** The unit of analysis is the human-ADAM pair. Performance attribution to either party individually is a category error. Design for the pair.

## 15. Open Questions

Areas where the platform will be generating knowledge the literature does not yet provide.

- **How much of a user's rationale do we show the next user?** When user A deviates in situation X with stated reason Y, and is proven wrong, and user B approaches situation X — do we show user A's rationale (teaches, but exposes) or just the bias class (anonymous, but less teaching power)? The answer probably depends on scope of validation and user consent; we will learn.

- **Should users see their own deviation history as a reflection surface?** "Here's where you've overridden, here's where those worked and where they didn't" could transform trust — or feel like a scorecard. Design carefully, likely opt-in.

- **How do we handle short-horizon wins that hide long-horizon damage without over-penalizing legitimate short-horizon victories?** Multi-horizon adjudication is specified in §9.5; the actual thresholds and aggregation will require empirical tuning.

- **What is the right cadence of time-pressured versus leisurely elicitation?** Too much time pressure fatigues and resents; too little invites confabulation. The per-user meta-learner should converge on this individually.

- **When does a validated learning get retired?** Market shifts, audience changes, and platform evolution will decay validated findings. Task 32's rollback-monitor logic applies, but the specific decay constants for teaming-loop learnings need calibration.

- **Does calibration transfer across platform domains the way it doesn't in prediction markets?** Open empirical question for us specifically — different from Tetlock's finding because our domains are structurally related via the bilateral cascade's shared ontology.

- **How do we probe nonconscious expert knowledge without running full implicit-association paradigms in the browser UI?** IAT-level latency protocols require controlled conditions. Approximations (TimedPair on meaningful stimuli, Fazio-style priming with SOA-controlled rendering) may recover most of the signal. TBD.

## 16. Bibliography

### Psychometrics and paired-comparison
Thurstone, L.L. (1927). *A Law of Comparative Judgment.* Psychological Review 34, 273–286. [PDF](https://parsmodir.com/wp-content/uploads/2013/02/thurstone1927.pdf)

Bradley, R.A. & Terry, M.E. (1952). *Rank analysis of incomplete block designs: the method of paired comparisons.* Biometrika 39, 324–345.

Tanner, W.P. & Swets, J.A. (1954). *A decision-making theory of visual detection.* Psychological Review 61, 401–409.

Green, D.M. & Swets, J.A. (1966). *Signal Detection Theory and Psychophysics.* Wiley.

Rafailov, R. et al. (2023). *Direct Preference Optimization: Your Language Model Is Secretly a Reward Model.* NeurIPS.

### Dual-process theory and automaticity
Bargh, J.A. (1990). *Auto-motives: Preconscious determinants of social interaction.* In Higgins & Sorrentino (eds.), Handbook of Motivation and Cognition vol. 2.

Bargh, J.A., Gollwitzer, P.M. et al. (2001). *The Automated Will.* Journal of Personality and Social Psychology 81, 1014–1027. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3005626/)

Epstein, S. (1994). *Integration of the cognitive and psychodynamic unconscious.* American Psychologist 49, 709–724.

Evans, J.St.B.T. & Stanovich, K.E. (2013). *Dual-process theories of higher cognition: Advancing the debate.* Perspectives on Psychological Science 8, 223–241. [SAGE](https://journals.sagepub.com/doi/10.1177/1745691612460685)

De Neys, W. & Pennycook, G. (2019). *Logic, fast and slow: Advances in dual-process theorizing.* Current Directions in Psychological Science 28. [PDF](https://gordonpennycook.com/wp-content/uploads/2020/02/de-neys-pennycook-2019.pdf)

Fazio, R.H. et al. (1986). *On the automatic activation of attitudes.* JPSP 50, 229–238. [PubMed](https://pubmed.ncbi.nlm.nih.gov/3701576/)

Greenwald, A.G., McGhee, D.E. & Schwartz, J.L.K. (1998). *Measuring individual differences in implicit cognition: The Implicit Association Test.* JPSP 74, 1464–1480. [PDF](https://faculty.washington.edu/agg/pdf/Gwald_McGh_Schw_JPSP_1998.OCR.pdf)

### Heuristics, biases, debiasing
Tversky, A. & Kahneman, D. (1974). *Judgment under uncertainty: Heuristics and biases.* Science 185, 1124–1131.

Kahneman, D. & Tversky, A. (1979). *Prospect theory: An analysis of decision under risk.* Econometrica 47, 263–292.

Schwarz, N. & Clore, G.L. (1983). *Mood, misattribution, and judgments of well-being.* JPSP 45, 513–523. [PDF](https://dornsife.usc.edu/norbert-schwarz/wp-content/uploads/sites/231/2023/11/83_jpsp_schwarz___clore_mood.pdf)

Schwarz, N. (1991). *Availability heuristic revisited: Ease of recall and content of recall.* In Heuristics and biases, Cambridge University Press.

Fischhoff, B. (1975). *Hindsight ≠ foresight.* Journal of Experimental Psychology: Human Perception and Performance 1, 288–299.

Nisbett, R.E. & Wilson, T.D. (1977). *Telling more than we can know.* Psychological Review 84, 231–259.

Morewedge, C.K. et al. (2015). *Debiasing decisions: Improved decision making with a single training intervention.* Policy Insights from the Behavioral and Brain Sciences 2, 129–140.

Morewedge, C.K. & Carey, S. (2020). *Debiasing transfers to the field.* [Wharton PDF](https://marketing.wharton.upenn.edu/wp-content/uploads/2019/12/01.06.2020-Morewedge-Carey-PAPER-DebiasingTransferstotheField.pdf)

### Introspective limits and tacit knowledge
Polanyi, M. (1966). *The Tacit Dimension.* University of Chicago Press.

Nonaka, I. & Takeuchi, H. (1995). *The Knowledge-Creating Company.* Oxford University Press.

### Human-machine teaming
Hutchins, E. (1995). *Cognition in the Wild.* MIT Press. [PDF](https://arl.human.cornell.edu/linked%20docs/Hutchins_Distributed_Cognition.pdf)

Hollnagel, E. & Woods, D.D. (2005). *Joint Cognitive Systems: Foundations of Cognitive Systems Engineering.* Taylor & Francis. [Page](https://erikhollnagel.com/books/joint-cognitive-systems-foundations.html)

Horvitz, E. (1999). *Principles of Mixed-Initiative User Interfaces.* CHI 1999. [PDF](https://erichorvitz.com/chi99horvitz.pdf)

Lee, J.D. & See, K.A. (2004). *Trust in automation: Designing for appropriate reliance.* Human Factors 46, 50–80. [PDF](https://csel.eng.ohio-state.edu/productions/intel/research/trust/Lee%20&%20See%20Trust%20Review.pdf)

Amershi, S. et al. (2014). *Power to the people: The role of humans in interactive machine learning.* AI Magazine 35, 105–120. [PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/amershi_AIMagazine2014.pdf)

Amershi, S. et al. (2019). *Guidelines for human-AI interaction.* CHI 2019. [ACM](https://dl.acm.org/doi/10.1145/3290605.3300233)

Gunning, D. & Aha, D. (2019, 2021). DARPA XAI program and retrospective. [Retrospective](https://onlinelibrary.wiley.com/doi/full/10.1002/ail2.61)

### Calibration and forecasting
Brier, G.W. (1950). *Verification of forecasts expressed in terms of probability.* Monthly Weather Review 78, 1–3.

Murphy, A.H. (1973). *A new vector partition of the probability score.* Journal of Applied Meteorology 12, 595–600.

Tetlock, P.E. & Gardner, D. (2015). *Superforecasting: The Art and Science of Prediction.* Crown Publishers.

Mellers, B. et al. (2014). *Psychological strategies for winning a geopolitical forecasting tournament.* Psychological Science 25, 1106–1115. [PDF](https://learnmoore.org/papers/Mellers%20et%20al%202014.pdf)

Haran, U., Moore, D.A. & Morewedge, C.K. (2010). *A simple remedy for overprecision in judgment.* Judgment and Decision Making 5, 467–476. [SPIES](http://fbm.bgu.ac.il/lab/spies/spies.html)

Speirs-Bridge, A. et al. (2010). *Reducing overconfidence in the interval judgments of experts.* Risk Analysis 30, 512–523.

### Chris Nocera's intellectual lineage (load-bearing)
Bargh, J.A. (various) — primary doctoral advisor. Automaticity research program.
Pinker, S. (1999). *Words and Rules: The Ingredients of Language.* Basic Books.
Williams, L.E. & Bargh, J.A. (2008). *Experiencing physical warmth promotes interpersonal warmth.* Science 322, 606–607.
Nocera, C. (various). Doctoral research on primary metaphor universals and physical-to-social neural recycling.
Ridley, M. (2003). *Nature via Nurture.*
Dawkins, R. (1976). *The Selfish Gene.*

### Naturalistic decision making (relevant tangent, not core cited)
Klein, G. (1998). *Sources of Power: How People Make Decisions.* MIT Press.

## 17. Glossary

*Bradley-Terry model.* Probabilistic model for pairwise preference: P(A beats B) = sA / (sA + sB). Mathematical substrate of RLHF.

*Brier score.* Mean squared error between a forecast probability and the eventual binary outcome. Lower is better. Proper scoring rule.

*Calibrated trust.* Correspondence between a user's trust in automation and the automation's actual capabilities.

*Claim (node type).* A user-asserted statement entered into the Dialogue Ledger with status "hypothesis" until instrumented, horizon-completed, and causally adjudicated.

*Confabulation.* A user generating a plausible-but-wrong explanation for their own behavior. Classic Nisbett & Wilson finding.

*Dialogue Ledger.* Neo4j subgraph recording every user-system interaction (claims, deviations, outcomes, calibrations).

*Elicitation mode.* The format of a question (ForcedPair, TimedPair, StoryPrompt, RecallabilityProbe, SPIES, etc.). Ten formats specified in §8.

*Horizon.* The expected time-to-causal-signal for a decision class. Causal adjudication cannot occur before horizon completion.

*Joint cognitive system.* The human plus the machine plus their shared artifacts, treated as the unit of analysis rather than the separate parties.

*Learning status.* The life-cycle state of a Claim: captured / instrumented / testing / validated_user_right / validated_system_right / indeterminate / retired.

*Loop A.* The analytics learning loop. Platform observes ad outcomes.

*Loop B.* The teaming learning loop. Platform elicits and tests human partner's claims.

*Mixed-initiative interaction.* Horvitz 1999 principles for shared AI-user initiative in collaborative systems.

*Plan-before-patch.* UX contract where the system shows its intended decision plan and rationale before rendering the actual change, allowing review.

*Recallability probe.* Follow-up question asking a user to recall a specific instance of a claim they just made, to discriminate tacit knowledge from confabulation.

*SPIES.* Subjective Probability Interval Estimates — bin-allocation protocol for calibrated range elicitation. Produces ~74% hit rate on nominal 90% intervals, vs ~30% for direct CI elicitation.

*Uncertainty Panel.* UI contract rendering a recommendation with three structured sections: Confident / Uncertain / Possibly Wrong, populated from existing evidence counts.

*Why Library.* Structured collection of validated bias patterns with triggers and countermeasures, queried at recommendation time for pre-emptive defensive reasoning.

---

**End of document.**
