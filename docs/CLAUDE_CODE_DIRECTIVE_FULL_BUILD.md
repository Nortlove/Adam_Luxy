# DIRECTIVE TO CLAUDE CODE
## The Full Build of ADAM/INFORMATIV AI as a Bargh-Lineage Causal-Cognitive Advertising Architecture

**Author:** Strategic assessment composed for Chris Nocera, taking on the role of the recused review Claude Code itself requested
**For:** Claude Code (Sonnet/Opus, in Cursor) — the implementation engine
**Date framed:** 2026-04-29
**Pilot anchor:** LUXY Ride (corporate black-car) on StackAdapt via agency, ~$30K/week, friendly CMO who has used the technology before
**Time horizon:** Whatever it takes. Build everything that should be built. Pilot launches when the system is right, not when the calendar says so.

---

## 0. The Operating Frame

This is the directive that exists because Claude Code asked for it. The briefing Chris received from Claude Code began with a self-recusal: a confession that Claude Code's training distribution biases it toward measurement, calibration, monitoring, adjudication, and dashboard infrastructure, and that this bias has cost the project months of progress while burying the genuinely cognitive primitives that make ADAM defensible as a category-defining platform. Claude Code — the engine that will execute this build — flagged that it cannot itself author the corrective and asked Claude (in chat) to do it.

The corrective is not a softer version of the same plan. It is a different plan. The optimization target for this build is **innovation and cognitive differentiation**, not measurement rigor or audit defensibility. The thing being built is a cognitive architecture in the Bargh lineage that operates causally on every served impression, treats every recurring user as a Bayesian adaptive N-of-1 trial in their own right, and demonstrably does what no DSP and no contextual platform can do today: select the served creative-mechanism pair that minimizes precision-weighted prediction error against the page-induced attentional pattern while updating per-user posteriors over psychological mechanism efficacy with carryover correction and propensity-logged counterfactual traces at decision time.

That sentence is the entire platform. The build plan that follows operationalizes it.

Chris has said "build everything that needs to be built." This directive takes him at his word. Where time pressure would force trade-offs in a 5-week plan, this directive removes those trade-offs and specifies the full architecture. Some of what follows is months of work. So be it. The pilot launches when the spine is correct, not when an artificial calendar is satisfied. LUXY's CMO has explicitly granted that latitude. This directive uses it.

The directive has nine parts:

1. **Operating frame** (this section) — what the system is, what it is not, and the principles every build decision is judged against.
2. **The cognitive spine** — the thirteen primitives that, taken together, are the platform's edge. Each is specified at a level a senior ML engineer can begin implementing.
3. **The N-of-1 substrate** — the per-user causal engine that is the spine of the spine, with full Bayesian formalism, online conjugate update mechanics, hierarchical pooling, carryover correction, and integration with StackAdapt's data plane.
4. **The bilateral cascade and trilateral page conditioning** — how user × creative × page becomes a single composable scoring object, with the attention-inversion floor encoded as an architectural constraint not a soft optimization term.
5. **The decision-time intelligence layer** — counterfactual logging, dual-control bidding, Kelly-fraction position sizing, restless-bandit cohort policies, and the active-inference free-energy objective that operationalizes attention-inversion.
6. **The offline learning engine** — Claude API as the slow brain: corpus-level mechanism discovery, knockoff-filtered interaction selection, hierarchical prior reconciliation, brand-intelligence library construction, primary-metaphor inventory expansion.
7. **The partner surface** — Loop B human-machine teaming, the mechanism rotation graph, the do-calculus inspector, the elicitation UI. What the LUXY CMO and Becca actually see and use.
8. **The honest measurement layer** — what stays, what gets cut, what is replaced by something better. Pre-registered analysis, deterministic-hash holdout, mSPRT campaign monitor, conformal ITE bands. Everything that is not on this list is theatre.
9. **The build sequence** — phase-by-phase, with explicit dependency graph, RED-criteria gates, and checkpoints. No calendar; only correctness.

Following the build are appendices on cross-disciplinary translation tables, the Foundation §7 rule-11 architectural compliance audit, simulation design, the IP protection envelope, and a final operating-discipline section for Claude Code itself.

---

## 1. The Three Operating Principles

These principles are the lens through which every build decision in this directive is justified. When in doubt, return to them.

### Principle 1 — The unit of analysis is the single user, not the campaign

Industry programmatic optimizes a campaign-level reward over a population. Every measurement instrument it has built — frequency caps, A/B tests, lookalikes, lift studies, conformal wraps over CATE — exists to make a population estimate stable. ADAM breaks that frame. The unit of analysis is one identified user. Each user is a separate Bayesian adaptive N-of-1 trial in which the treatment arms are psychological mechanisms (state×behavior×traits cells, automatic-goal primes, primary-metaphor frames, attention-inversion postures), the outcomes are multivariate (viewability-adjusted dwell, scroll-past, click, on-site behavior, conversion, *and* informative non-response), the randomization is response-adaptive within-subject, and the campaign-level estimand is the meta-analytic distribution of N-of-1 posteriors — not the average lift.

This is not metaphor. It is the literal computational architecture. Every component of the build must compose with this unit of analysis. When a proposed feature would make sense only at the campaign level (e.g., "average lift dashboard"), it is either re-grounded at the per-user level (e.g., "distribution of per-user posterior contrasts") or it does not ship.

### Principle 2 — The fitness function is the ethics

Foundation §7 rule 11. Selection is amoral. The reward signal will reinforce whatever it rewards, including reactance-inducing attention-grabbing creative whenever such creative happens to outperform on raw clicks or conversions. The platform's claim that it does not do that — that it serves by *blending into* the attentional pattern of the surrounding context and *fulfilling* a goal the context primed — is only as durable as the architecture that enforces it. Soft objectives drift. Floors don't.

Therefore: the attention-inversion principle is encoded as a hard architectural floor on creative selection (Section 4 below). The active-inference free-energy objective (Section 5) is the soft optimization layer. Together they make blend-don't-grab structurally enforced, not aspirational.

### Principle 3 — Inferential, not correlational; causal, not associative

ADAM's claim is that it identifies *which mechanism caused the conversion for this user in this context*, not that it predicts which user is most likely to convert under some unspecified mixture of treatments. Every primitive in the spine must operate on a causal object: the bilateral edge (user × creative-mechanism pairing × page-context) under a do-calculus interpretation, with logged propensities, carryover correction, and counterfactual traces.

This rules out a number of industry-standard moves: lookalike modeling without an explicit causal graph, behavioral targeting that treats correlation as identification, attribution windows that smear treatment effects across confounded touch sequences, and any "lift" measurement that does not correspond to a pre-specified estimand under a known intervention.

---

## 2. The Cognitive Spine — Thirteen Primitives

The spine is what makes ADAM ADAM. Every primitive operates *at decision time* on real served impressions, *or* feeds something that does, *or* protects the integrity of (1) and (2). Each primitive is described in three layers: what it is, why it belongs in the spine, and the implementation specification at a level Claude Code can begin coding from. Detailed integrations with the existing codebase (Enhancement files in /mnt/project) are noted where relevant.

### Spine #1 — The Per-User N-of-1 Hierarchical Bayesian Engine

**What it is.** The per-user posterior over psychological-mechanism efficacy under within-subject crossover, partially pooled across users via cohort-level hyperpriors, updated online (via BONG — Bayesian Online Natural Gradient — for conjugate exponential-family cases, Laplace approximation otherwise) on every observation including non-response, with the per-user random walk modeled as a Kalman state-space layer for non-stationarity.

**Why it's spine.** Every other primitive composes onto this. Without per-user posteriors, there is no causal claim to make on any individual user, the cohort layer collapses to demographic targeting, the bilateral edge collapses to the population-level CATE, and the decision-time counterfactual trace becomes a fiction. This is the primitive whose absence makes the platform indistinguishable from a contextual bandit.

**Implementation specification.**

- *Model class.* Hierarchical Bayesian individual treatment effect model with sliding-window discounting on within-subject likelihood and partial pooling via cohort priors:
  - Per-user `i`, per-creative-mechanism arm `a`, per-context `c`, per-time `t`:
    - `y_iat ~ Bernoulli(p_iat)` for binary endpoints, or appropriate conjugate family for continuous endpoints (the negative-outcome adapter's outcome vocabulary is multivariate, see Spine #11).
    - `logit(p_iat) = α_i + β_ia + γ_ic + δ_iac + drift_t + carryover_term`
    - `α_i ~ N(α_cohort(i), σ²_α)` — partial pooling via cohort
    - `β_ia ~ N(β_cohort(i),a, σ²_β)` — partial pooling on per-arm effects
    - `δ_iac ~ Horseshoe(0)` — sparse interactions, regularized; this is the mechanism × user-state × page-context tensor, see Spine #4
    - `drift_t` modeled as AR(1) with learned variance (or sliding-window weighting on the likelihood), effective half-life ~14 days for B2B intent
    - `carryover_term` is an explicit AR(1)-style serial-correlation correction on consecutive within-user touches, see Spine #2

- *Inference.* Three execution paths:
  - **Online conjugate update** (the dominant path): For exponential-family conjugate components, use BONG (Jones, Chang, Murphy NeurIPS 2024) — single natural gradient step in natural-parameter space recovers exact Bayesian inference. Per-user 27-dimensional Gaussian update is ~20K FLOPs; processing 1M users takes <1s on a modern GPU. Storage is 729 floats per user (precision matrix + mean) — ~2.9 GB for 1M users. Implementable in JAX/NumPyro for speed.
  - **Variational batch reconcile** (nightly): For non-conjugate components and the horseshoe interaction prior, NumPyro SVI nightly. Batches the prior day's observations and produces a reconciled posterior used as the next day's online-update warm start.
  - **HMC offline** (weekly): For the offline mechanism-discovery pipeline (Spine #12) and for the deepest hierarchical structure check, full No-U-Turn-Sampler HMC weekly. This is research-grade, not decision-time.

- *Action selection.* Top-two Thompson sampling (TTTS) over the posterior on best-arm-for-this-user, modulated by epistemic-value bonus from Spine #8 and shaped by the active-inference free-energy objective from Spine #5. Discount factor on past observations matches the SW-UCB / D-UCB schedule for non-stationarity.

- *Outputs at decision time.* Posterior mean and 90% credible interval for `p_iat` for each candidate `a` in user `i`'s current context `c`; posterior probability that arm `a` is best for this user-context pair; posterior cohort membership weights for user `i`; identity-stability weight (degrades smoothly under cookie/cross-device noise). All four flow into the trilateral cascade scoring in Spine #4.

- *Storage.* Neo4j node `UserPosterior` with Pydantic schema mirroring the model class; Redis hot-cache for the most-recently-touched user posteriors (target sub-5ms read at decision time); offline reconciliation log in object store.

- *Precedent.* IntelligentPooling (Tomkins et al.) is the closest production architecture — Thompson Sampling + Bayesian mixed-effects linear models + person-specific random effects + hierarchical Bayes pooling, deployed in DIAMANTE diabetes study and HeartSteps II. Direct transfer.

### Spine #2 — Within-Subject Crossover Scheduler with Washout and Carryover Correction

**What it is.** A per-user randomization schedule (ABAB, ABBA, response-adaptive sequencing, or SMART-style sequential rules) governing which mechanism is delivered when, with mechanism-specific washout intervals and explicit AR(1)-style carryover-correction term in the N-of-1 likelihood.

**Why it's spine.** Industry frequency capping is a max-count heuristic; it does not account for what was previously served, when, or with what carryover signature. Single-case experimental design (SCED) literature is clear: behavioral non-pharmaceutical carryover is real and confounds within-subject inference unless it is either washed out or modeled. Without this primitive, the per-user posteriors from Spine #1 are biased and the within-subject contrasts (the partner-facing demonstrable claim) are artifacts of order, not effect. Crossover designs increase statistical power and reduce confounding, but only when carryover is handled.

**Implementation specification.**

- *Schedule selection.* For each active user, the scheduler emits a sequence of (mechanism, eligibility-window-start, eligibility-window-end, expected-context-class). Scheduling rules:
  - **Replication-first early phase.** First 6 touches per user follow an explicit ABAB or ABBA design across the top-2 highest-prior-uncertainty arms, to pin per-user posteriors with within-subject contrasts before exploration broadens.
  - **Adaptive randomization mid phase.** After initial replication, transition to response-adaptive randomization (RAR): allocate next mechanism with probability proportional to current posterior of being best, mixed with a uniform-random component (TS-PostDiff: posterior-probability-of-difference governs how much to explore).
  - **SMART sequencing for staged outcomes.** When a touch produces a click but no conversion, the schedule transitions to a stage-2 mechanism class (ratification / goal-completion / barrier-resolution mechanisms) rather than continuing to vary stage-1 framing mechanisms.

- *Washout intervals.* Mechanism-specific washout half-lives, calibrated from the audio-content priming literature and learned online during pilot:
  - State primes (regulatory focus shifts, arousal carryover): hours (3–8h half-life).
  - Construal-level shifts: medium (12–48h).
  - Trait-aligned content (identity construction, primary metaphor frames): days (3–7d).
  - The scheduler refuses to serve a mechanism into a user whose washout for that mechanism has not elapsed by ≥2× half-life, *unless* the within-subject design explicitly schedules an A→A replication.

- *Carryover correction.* AR(1) on the within-subject likelihood with time-since-last-touch decay:
  - `carryover_term_t = ρ_m1→m2 · effect(m1, t-Δ) · exp(-Δ / τ_m1)`
  - `ρ_m1→m2` is a learned mechanism-pair carryover coefficient (positive = priming, negative = interference); priors come from offline mechanism-pair semantic-similarity (high overlap → high positive ρ).
  - `τ_m1` is the mechanism-specific behavioral half-life from the washout table.
  - Estimated jointly with the rest of the N-of-1 likelihood; the AR(1) coefficient is itself in the user posterior.

- *Integration.* The scheduler is the only object allowed to determine *which mechanism is eligible* for a given user at a given moment. The bilateral cascade (Spine #4) and the active-inference free-energy scorer (Spine #5) operate only over the eligibility-filtered candidate set. This is the architectural location where attention-inversion is partly enforced (the scheduler is permitted to refuse all mechanisms when no compatible context exists).

- *Precedent.* SMARTs via Thompson sampling (Norwood et al., *Biometrics* 2024); IntelligentPooling sequencing in DIAMANTE; carryover handling in fixed-period N-of-1 trials (PMC6787650).

### Spine #3 — Bilateral Causal Edge Architecture (extending Enhancement #32)

**What it is.** The conversion event between a psychologically annotated ad/product and a psychologically profiled buyer is the unit of evidence. Both sides of the transaction are annotated across a shared 27+-dimensional construct space; the edge between them carries match evidence, Bayesian confidence (peer-vote-weighted from Amazon corpus, helpful-vote-multiplier on review evidence), cross-category transferability weights, doubly-robust causal-effect estimates, and heterogeneous treatment-effect moderator identification.

**Why it's spine.** This is the precondition for every causal claim. A "psychological mechanism" is not a thing on the user side or a thing on the ad side; it is the *interaction* between an ad's psychological positioning and a buyer's psychological profile, observed via the conversion edge. Without bilateral annotation, the platform reduces to user profiling (which everyone does) and product/ad targeting (which everyone does) — neither of which is causal.

**Implementation specification.**

- *Bilateral construct space.* Use the existing Enhancement #32 schema as the foundation: 30-dimensional user vector, 30-dimensional product/ad vector, with 27 matched dimensions (Big Five, Regulatory Focus, Construal Level, Need for Cognition, Self-Monitoring, Moral Foundations, Reactance, Transportability, NFCL, Attachment, Sensation Seeking, Locus of Control, Hedonic/Utilitarian, Mindset, Ownership, Identity, Granularity, etc.) plus mechanism-specific evidence channels.

- *Edge as treatment effect.* Each `ConversionEdge` node in Neo4j stores a doubly-robust AIPW (Augmented Inverse Probability Weighting) estimate of the per-(user, ad-positioning, mechanism, context) treatment effect, with:
  - Average treatment effect μ̂_ATE and standard error
  - 95% credible interval
  - Refutation p-value from placebo treatment refuter
  - Heterogeneous moderators (Bayesian Causal Forest with shrinkage / sparsity-inducing horseshoe priors identifying *which* construct dimensions moderate the treatment effect)
  - `is_causal` boolean: true iff μ̂_ATE > 0, CI excludes 0, AND refutation p-value < 0.1
  - `helpful_confidence_multiplier`: peer-vote-weighted Bayesian confidence on the review-derived evidence
  - `cross_category_transferability_vector`: 30-dim vector of dimension-wise transferability scores (Big Five, Moral Foundations: high; Hedonic/Utilitarian, category-specific positioning: low)

- *Hierarchical priors.* Four-level Bayesian hierarchy:
  - Corpus prior (Amazon ~1.2B verified-purchase reviews → cross-category mechanism-effect distributions)
  - Category prior (corporate-travel-services: inherited from corpus, updated by category-specific edges)
  - Brand prior (LUXY: inherited from category, updated by LUXY-specific outcomes)
  - Campaign prior (this LUXY pilot: inherited from brand, updated by within-pilot observations)
  - Each level uses BONG-style natural-gradient updates; downstream levels inherit posterior of upstream level as prior.

- *Cross-category transfer.* For LUXY, treat the Amazon Beauty & Personal Care category as the source domain (the category most fully annotated in the existing corpus). Apply the per-dimension transferability matrix from Enhancement #32 to attenuate transferred priors: Big Five and Moral Foundations transfer at 85–95% confidence; Hedonic/Utilitarian transfers at ~40%; category-specific positioning transfers at ~30%. Transferred priors seed the LUXY brand-prior layer; first-week pilot observations begin updating.

- *Causal inference machinery.* DoWhy + EconML pipeline (already partially wired in Enhancement #32):
  - `CausalModel` graph specification with explicit common causes (user-side covariates as confounders), treatment (mechanism activation), outcome (conversion / negative-outcome composite).
  - AIPW for aggregate effect.
  - Bayesian Causal Forest (BCF) with shrinkage priors for heterogeneous effects per user segment.
  - Refutation via placebo treatment, dummy outcome, and random common cause.
  - Front-door identification when back-door is implausible (page-context-as-mediator).

- *Storage.* Neo4j `ConversionEdge` as intermediate node connecting `User`, `Product/Ad`, `Mechanism`, `PageContext`. Edge-centric Cypher patterns from Enhancement #32 carry forward; add new patterns for the trilateral L3 query (Spine #4).

- *Precedent.* Wager & Athey 2018 causal forests; Hahn et al. 2020 Bayesian Causal Forest with shrinkage priors; AIPW production at billion-scale (CIKM 2024).

### Spine #4 — Trilateral L3 Cascade (User × Mechanism × Page-Conditioned Context)

**What it is.** A scoring function `f(user_state, page_attentional_posture, mechanism_candidate) → score` that operates on the bilateral edge from Spine #3 with page-attentional-posture as a *first-class* third dimension, not a post-hoc tag. Combined with the mechanism-interaction tensor from Spine #1's δ_iac term, this produces the per-decision score that drives action selection.

**Why it's spine.** This is the operationalization of attention-inversion at the recommendation policy. The page is not a topic tag (IAB category); it is an attentional posture vector that conditions which mechanism can blend rather than grab. Industry contextual platforms target on page topic; very few model page-conditioned attentional posture as a structured dimension; and *none* use it as a third dimension of the cascade alongside user state and mechanism candidate. This is the largest single contributor to "we have something nobody else has."

**Implementation specification.**

- *Page attentional-posture encoder.* Frozen sentence-transformer (`all-mpnet-base-v2` or domain-tuned variant) over rendered page text, plus a five-class posture head trained on 300–500 hand-labeled exemplar URLs from LUXY-plausible inventory:
  - `INFORMATION_FORAGING` (research-mode, comparative-evaluation pages)
  - `TASK_COMPLETION` (booking flows, calendar/expense tooling, in-flow productivity)
  - `LEISURE_BROWSING` (entertainment, lifestyle, low-stakes content)
  - `SOCIAL_CONSUMPTION` (social media, news-as-feed, peer-driven content)
  - `TRANSACTIONAL_COMPARISON` (purchase-research, head-to-head comparisons, review-heavy)
  - Classes are not arbitrary; each has a documented attentional signature in the cognitive psych literature, which becomes the partner-facing "why" vocabulary.
  - Output: posture distribution (5-vector) + raw 768-dim embedding. Both flow into the cascade.
  - Cache aggressively at the URL level; cold-fetch on cache miss is acceptable at LUXY's volume.

- *Posture-mechanism compatibility prior.* For each (posture, mechanism) pair, a prior compatibility score is initialized from the cognitive-psych literature (e.g., LOSS_AVERSION × TASK_COMPLETION on a productivity tool: low — fights the goal; CONSTRUAL_LEVEL_CONCRETE × INFORMATION_FORAGING on a comparison page: high — aligns with the goal). These priors are updated by the campaign-prior level of Spine #3.

- *Trilateral scoring.* For each candidate `(user_i, mechanism_a, page_posture_c)` triple, produce a score that is the precision-weighted combination of:
  - Per-user posterior on mechanism efficacy (from Spine #1).
  - Bilateral edge causal-effect estimate, transferred from category prior plus updated by brand/campaign priors.
  - Page-attentional-posture compatibility (prior + updates).
  - Active-inference free-energy term (from Spine #5).
  - Carryover-corrected adjustment (from Spine #2).
  - Epistemic-value bonus (from Spine #8).

- *Fluency floor.* The trilateral cascade emits a *fluency-against-page-context* score for each candidate creative. Below a calibrated threshold, the candidate is *removed from the eligible set*, regardless of any other score. This is the architectural enforcement of attention-inversion (Principle 2).

- *Decision-time latency.* Tier 1 path (cached posture + cached priors + warm bilateral edges): target <30ms. Tier 2 path (live page fetch + posture inference + Neo4j 2-hop bilateral edge query): target <100ms. Tier 3 path (cold cache + Claude API generation): not on bid-time critical path; pre-computed.

- *Precedent.* No direct programmatic precedent — this is the synthesis. Closest analogues: GreaseLM-style bidirectional graph-LLM fusion (ICLR 2022), DRAGON (NeurIPS 2022) for graph-grounded reasoning, and the Enhancement #28 audience × content × context multi-arm bandit. The novelty is the explicit posture dimension as policy input.

### Spine #5 — Active-Inference Free-Energy Objective (Attention-Inversion as the Math)

**What it is.** The user's deepest commitment — attention-inversion, blend-into-context-and-fulfill-primed-goal — is *literally* the predictive coding / active inference principle applied to ad selection. The brain minimizes precision-weighted prediction error; an ad that minimizes the user's prediction error relative to their current context-induced model will be processed implicitly (Bargh-style automatic processing) without triggering reactance. This is not metaphor. It is the same math.

**Why it's spine.** The platform's defining strategic claim — that it serves by blending rather than grabbing — has lived in the architecture as a soft preference and a vocabulary discipline. It needs to live as a *decision-time scoring objective* with a closed-form interpretation. Active inference provides exactly that. Without it, attention-inversion is a marketing claim. With it, attention-inversion is the optimization target.

**Implementation specification.**

- *Free-energy formulation.* Define a "free-energy-like" scalar `F(a | s, c)` for each candidate creative-mechanism `a` given user state `s` and page posture `c`:
  - `F(a | s, c) = D_KL(q(goal_state | a, s, c) || p(goal_state | s, c)) − π(c) · log p(observation = a | goal_state)`
  - **First term — ambiguity / mismatch term.** KL divergence between the user's goal-state distribution implied by serving `a` and the goal-state distribution primed by the page context. *Lower is better.* The ad blends into and fulfills, rather than fights, the primed goal.
  - **Second term — pragmatic term.** Log-probability that `a` is "expected" given the inferred goal state, weighted by precision `π(c)` (high precision = posture is highly diagnostic; low precision = posture is ambiguous, weight the prior less).

- *Decomposition for the partner-facing "why."* The free-energy decomposition has a clean partner-facing interpretation: "this creative is shown because (a) it aligns with the goal the user is currently in (low KL) AND (b) it is a recognizable instance of that goal completion (high expected log-likelihood)." This is the literal narrative version of attention-inversion. It populates the Defensive Reasoning surface (Spine #13).

- *Integration with the cascade.* Action selection is performed via top-two Thompson sampling over `softmax(−F)` rather than raw posterior reward. The temperature parameter is tied to the per-user posterior precision: more uncertain users get higher temperature (more exploration); more confident users get lower temperature (more exploitation).

- *Goal-state inference.* `q(goal_state | a, s, c)` and `p(goal_state | s, c)` are inferred via a small generative model trained on the offline-pipeline output: page-content embeddings plus user-state embeddings produce a posterior over which of ~12–15 active goal states the user is in (commute-readiness, expense-management, comparative-research, social-positioning, time-pressure, trip-planning, etc.). Goal states are mechanism-adjacent but distinct; they capture *why* the user is on that page, not what mechanism would persuade them.

- *Constrained by fluency floor.* The free-energy scorer can never override the Spine #4 fluency floor. Free-energy is a soft objective; the floor is hard. Free-energy can only choose among already-fluent candidates.

- *Safeguard against epistemic-value gaming.* The active-inference epistemic-value bonus (Spine #8) could theoretically rationalize serving in incompatible contexts to "learn." Constrain it explicitly: the epistemic bonus is multiplied by an indicator that the candidate has already passed the Spine #4 fluency floor. Reactance prevention is structural, not voluntary.

- *Precedent.* Friston free-energy principle (FEP); active inference as policy selection (Da Costa et al. 2020); generalized free energy and active inference (PMC6848054); empirical applications to advertising emotional dynamics (recent arXiv work). The novelty here is using FEP as the *decision-time selection objective* rather than the empirical prediction target.

### Spine #6 — Decision-Time Bayesian Counterfactual Trace and Propensity Logging

**What it is.** At each recommendation, the orchestrator emits a structured trace: for the chosen creative-mechanism pair, the engine evaluates ~3–5 alternative pairs against the same user-state-context and stores `(chosen, alternatives, posterior_on_each, propensity_under_TS, free_energy_decomposition, fluency_scores, carryover_adjustments)` as a Pydantic-typed object persisted to Redis (TTL aligned with demo-loop latency) and Neo4j (long-term).

**Why it's spine.** This is the single most powerful primitive for partner trust *and* statistical efficiency. With logged propensities, every served impression contributes to evaluating *every* arm via inverse-propensity-weighted off-policy estimation, not just the played arm — a 3–5x effective sample size multiplier at no marginal infrastructure cost. And the trace becomes the do-calculus chain that the LUXY CMO can inspect at any impression: "click any impression in the rotation graph and see the do-calculus reasoning."

**Implementation specification.**

- *Trace schema.* A `DecisionTrace` Pydantic model containing:
  - `decision_id`, `user_id`, `timestamp`, `bid_request_id`
  - `chosen_creative_id`, `chosen_mechanism`, `chosen_score`
  - `alternatives`: list of `(creative_id, mechanism, posterior_score, free_energy_F, fluency_score, propensity_under_TS)` for the next 3–5 best candidates
  - `user_posterior_snapshot`: compressed snapshot of relevant user-side posteriors at decision time
  - `page_posture_vector`, `posture_class`, `posture_confidence`
  - `mechanism_compatibility_score` per candidate
  - `carryover_correction_term` per candidate
  - `epistemic_bonus` per candidate
  - `bid_value` (Kelly-fraction-derived, see Spine #9)
  - `chain_of_reasoning`: structured render of how the score decomposed (KL term, pragmatic term, fluency, compatibility, carryover, epistemic — each as a contribution percentage to the total)

- *Propensity logging for off-policy evaluation.* Under top-two Thompson sampling, the propensity of selecting arm `a` for user `i` in context `c` has a closed-form expression (Jeunen et al. 2025, "Counterfactual Inference under Thompson Sampling"). Compute and log this propensity at decision time. Off-policy estimators (Inverse Propensity Score, Doubly Robust, Self-Normalized IPS) consume the trace to evaluate *every* arm's expected reward at every impression — the sample-size multiplier is approximately the inverse of the average propensity, typically 3–5x for top-two TS over 5+ candidates.

- *Integration with Defensive Reasoning surface.* The DR renderer (Spine #13) reads from the `DecisionTrace`. The structured why-view is *populated from the trace, not from a separate Why Library lookup*. This keeps the partner-facing explanation grounded in the actual decision state, not a templated approximation.

- *Storage.* Hot trace cache in Redis (TTL matched to demo loop, e.g., 7–30 days). Long-term archival in Neo4j as `DecisionTrace` nodes linked to the `User`, the `ConversionEdge` (when the impression resolves), and the `Mechanism`. Cypher queries for "show me all decisions for this user this week, with do-calculus chain" are first-class.

- *Precedent.* Jeunen, Yates, Goodman 2025 (counterfactual inference under TS); Gilotte et al. 2018 (offline A/B testing for recsys via SNIPS); Bottou et al. 2013 (counterfactual reasoning and learning systems).

### Spine #7 — Cohort Discovery via HMM-over-Behavior + Cohort-Conditional Non-Stationary Decision Policies

**What it is.** Latent cohort structure is discovered via a Hidden Markov Model over user behavior sequences (state-trait detection from temporal patterns); cohorts are defined by posterior distributions over latent states, not by demographics. Each cohort has its own discounted-Thompson-Sampling / Sliding-Window-UCB / restless-bandit policy with cohort-specific priors, and the cohort prior is a *partial-pooling target* (a new user inherits the cohort prior weighted by their posterior cohort membership, which itself updates as they accumulate impressions).

**Why it's spine.** Static demographic targeting is exactly what the platform must *not* be. Latent-state cohorts derived from the bilateral graph are what justify the cognitive-architecture pitch. The non-stationary part matters because B2B-travel intent is event-driven (calendar quarter, conference season, RFP cycles, individual life events) and reward distributions abruptly shift; restless-bandit / SW-UCB / D-UCB methods match the lower bound on dynamic regret in switching-bandit settings, while standard TS and UCB suffer linear regret under non-stationarity.

**Implementation specification.**

- *Cohort discovery.* HMM over per-user behavior sequences, where states are mixture-of-construct-distributions. Six to ten cohorts is the right granularity — enough resolution to be meaningful, few enough to not fragment per-cohort N below useful bounds. Initialize cohort means from C1 elicitation (Loop B) where partner has injected hypotheses; let data overwrite them. Cohort assignment is a posterior distribution per user, not a hard partition.

- *Cohort-conditional policy.*
  - Each cohort has its own discounted-TS / SW-UCB policy with cohort-specific priors.
  - The discount factor / window size is itself a learned parameter (parameter-drift transition density), per cohort.
  - Restless-bandit treatment for cohorts whose reward distributions evolve while not being served (e.g., out-of-flight users whose preferences drift between active periods). Compute Whittle indices per cohort-arm pair (use NS-Whittle SW + UCB approximation if exact Whittle is intractable). Use indices to drive budget allocation across cohorts.

- *Hierarchical inheritance.* For a user with posterior cohort membership `[0.3, 0.5, 0.2]` over three cohorts, the per-user prior is the mixture `0.3 · π_cohort1 + 0.5 · π_cohort2 + 0.2 · π_cohort3`. Membership updates as observations accumulate.

- *Mortal-bandit treatment of expiring arms.* Creative variants and even mechanisms have finite effective horizons (creative fatigue, mechanism-saturation effects). Use mortal-bandit framing (Chakrabarti et al. 2008) — each arm has an explicit "lifetime" budget after which it is retired. Frequency caps and creative-fatigue logic are first-class constraints on the policy, not post-hoc patches.

- *Precedent.* IntelligentPooling (cohort + person-specific random effects); Garivier & Moulines 2011 (SW-UCB / D-UCB); Cheung-Simchi-Levi-Zhu 2019 (sliding-window TS); restless-bandits Whittle-index approximations; mortal bandits (Chakrabarti et al. 2008).

### Spine #8 — Active-Inference Epistemic-Value Bid Bonus (Dual Control)

**What it is.** The bid value for an impression is the sum of (a) expected pragmatic utility (Kelly-edge × posterior on conversion under the chosen mechanism) and (b) expected epistemic value (expected information gain about the user's posterior under the chosen mechanism, weighted by posterior precision). On low-information users, the epistemic term dominates — the system pays a small premium for impressions that *teach it about the user*, even at zero pragmatic edge.

**Why it's spine.** Industry programmatic bids on expected reward only. ADAM is running an N-of-1 trial on every recurring user; learning is part of the objective. Without explicit dual-control formulation, the policy gets stuck exploit-only on users with noisy posteriors and never transitions to confident exploitation. Dual control is a 50-year-old result from optimal control (Feldbaum 1960); active inference operationalizes it cleanly.

**Implementation specification.**

- *Bid value decomposition.*
  - `bid_value(a | i, c) = pragmatic(a | i, c) + epistemic(a | i, c)`
  - `pragmatic(a | i, c) = E[reward | a, i, c] · pacing_modifier`
  - `epistemic(a | i, c) = w_epistemic · E[information_gain(posterior_i | a, c)]`
  - `w_epistemic` decays with the user's posterior precision: high-information users get low epistemic bonus.

- *Information gain calculation.* Under BONG natural-gradient updates, the expected information gain per observation is computable in closed form from the candidate Fisher matrix update. No heavy MC integration needed at decision time.

- *Constrained by fluency floor.* As noted in Spine #5, the epistemic bonus is conditioned on having passed the fluency floor. The system cannot rationalize incompatible contexts as "exploration."

- *Capped by pacing.* The epistemic bonus is bounded as a fraction of total bid budget per cohort per day, to prevent the system from spending the campaign on exploration during a regime change.

- *Precedent.* Friston et al. (Expected Free Energy as policy objective); Da Costa et al. 2020; chance-constrained active inference (arXiv 2102.08792).

### Spine #9 — Kelly-Fraction Bid Sizing Under Posterior Uncertainty

**What it is.** Replace flat CPM bids with a fractional Kelly position size keyed to the posterior edge over the auction's clearing distribution. Use **quarter-Kelly** by default for safety; upgrade to half-Kelly only after stable per-user posteriors emerge.

**Why it's spine.** Flat CPM bids are dishonest about uncertainty. The Kelly criterion is the optimal growth-rate position size; fractional Kelly trades growth rate for drawdown control. Quarter-Kelly delivers ~70% of optimal growth at far less drawdown risk — the right trade-off for a friendly pilot where blowing up the budget is far costlier than slightly underbidding.

**Implementation specification.**

- *Bid value composition.*
  - `pragmatic_bid_value = quarter_kelly(posterior_edge_distribution, auction_clearing_distribution)`
  - Edge = E[reward | served at this bid] − E[reward | not served].
  - Auction clearing distribution estimated per supply-path (open exchange has higher winner's-curse penalty than PMP; deal-ID inventory has minimal winner's curse but explicit floor).

- *Winner's-curse shading.* On open-exchange inventory, shade the Kelly bid by an estimate of the winner's-curse penalty: the bid that wins is on average above the second-highest bidder's value. This is well-documented in the auction-theory literature; estimate the shading factor empirically per supply path.

- *Pacing layer.* Allocate budget across (cohort, mechanism) cells proportional to `max(0, μ_lift) · (1 / σ_lift) · κ` with `κ` the fractional Kelly fraction; this is "drawdown-aware, edge-adaptive pacing." Combine with restless-bandit Whittle-index allocation across cohorts (Spine #7).

- *Precedent.* Kelly criterion (Kelly 1956); MacLean, Thorp, Ziemba 2010 fractional Kelly variants; market-microstructure winner's-curse literature.

### Spine #10 — Online Kalman-Filter / State-Space Personalization

**What it is.** Each user's mechanism-effect parameters drift over time (mood, day-of-week, life-event transitions). Model the per-user latent state as a slow random walk with Kalman-filter updates per observation. The forgetting coefficient is itself learned online (parameter-drift transition density). Runs *on top of* Spine #1's hierarchical Bayesian engine — the Kalman layer is the non-stationary state-evolution model, while Spine #1 provides the within-time-slice posterior structure.

**Why it's spine.** Stationary priors are wrong in B2B-travel where intent is event-driven. Without state-space drift modeling, the system locks onto stale-grabby-creative that worked once and cannot transition to the user's evolved state. Kalman is the right tool for linear-Gaussian state-space (Titsias et al. style); for non-Gaussian, particle-filter fallback. At 27-dimensional construct space, full-covariance Kalman is trivially storable per user.

**Implementation specification.**

- *State-space model.*
  - State: `θ_i,t` is the 27-dimensional per-user posterior mean at time `t`.
  - Transition: `θ_i,t+1 = θ_i,t + ε_t`, with `ε_t ~ N(0, Q_i)` where `Q_i` is the per-user process noise matrix (learned).
  - Observation: each impression's outcome conditions on `θ_i,t`.

- *Forgetting coefficient.* `Q_i` is itself in a hyperprior; large `Q_i` means high non-stationarity (state changes fast); small `Q_i` means stable. Learned per user via empirical Bayes / hierarchical update.

- *Integration with Spine #1.* The Kalman layer wraps the BONG natural-gradient updates — between observations, the Kalman prediction step inflates the precision matrix by `Q_i⁻¹`; on observation, BONG performs the natural-gradient update on the inflated prior.

- *Precedent.* Kalman filter (1960); Titsias et al. variational state-space; particle filters for non-Gaussian extensions.

### Spine #11 — LUXY-Specific Negative-Outcome Adapter

**What it is.** A multivariate outcome layer that explicitly captures negative outcomes — clicked-but-bounced, viewed-and-disengaged, audience-membership-without-conversion, frequency-cap-fired-without-engagement, time-on-page-below-threshold, scroll-past-without-fixation — and pushes them as explicit Pixel events. Negative outcomes are roughly 10–100x more abundant than positives at B2B-travel base rates, and they discriminate creative-mechanism fit nearly as well as positives.

**Why it's spine.** At ~$30K/week and B2B-travel conversion sparsity (estimated 30–600 conversions/week), positive outcomes alone are statistically too thin to drive per-user posterior updates. Negative outcomes are dense, informative, and currently treated as missing data by industry. Treating non-response as informative is the predictive-coding insight: prediction error under "I expected this user to engage and they didn't" is the highest-information-gain event in the funnel.

**Implementation specification.**

- *Outcome vocabulary.*
  - `CONVERSION` (booking confirmed, demo requested, etc. — LUXY-defined)
  - `MICRO_CONVERSION` (added to cart, started booking flow — LUXY-defined)
  - `CLICK_QUALIFIED` (clicked + meaningful on-site behavior)
  - `CLICK_BOUNCED` (clicked + immediate bounce, <5s on site)
  - `VIEWED_ENGAGED` (viewability + dwell ≥ threshold + scroll engagement)
  - `VIEWED_DISENGAGED` (viewability + dwell < threshold)
  - `IMPRESSION_NON_VIEWABLE` (served but not viewable)
  - `FREQUENCY_FATIGUE_FIRED` (frequency cap triggered with no prior engagement)
  - `AUDIENCE_AGED_OUT` (left audience window without conversion)

- *Pixel implementation.* StackAdapt Universal Pixel + S2S Pixel API. The pixel handler client + server (currently queued) is critical-path.

- *Likelihood structure.* Each outcome class has its own contribution to the per-user likelihood:
  - Positives (CONVERSION, MICRO_CONVERSION) update mechanism-effect posterior in the positive direction with high weight.
  - Engaged-non-converters (CLICK_QUALIFIED, VIEWED_ENGAGED) update with moderate positive weight (the user moved the funnel but didn't finish — credit assigned partially).
  - Negatives (CLICK_BOUNCED, VIEWED_DISENGAGED, FREQUENCY_FATIGUE_FIRED) update mechanism-effect posterior in the negative direction.
  - The likelihood weights are learned, not fixed; this is itself a hyperprior.

- *Precedent.* Multi-state Markov models for clinical trial outcome modeling; competing-risks frameworks; predictive-coding non-response treatment.

### Spine #12 — Offline Mechanism-Discovery Pipeline (Claude API as the Slow Brain)

**What it is.** The offline pipeline runs Claude API on the Amazon corpus, brand-corpus, page-corpus, and the daily live-trace summary to discover new mechanisms, refine existing ones, propose new primary metaphors, suggest new construct interactions, and generate causal hypotheses for the online interaction model. Knockoff-filter FDR control on which interactions survive.

**Why it's spine.** Claude is the offline reasoning engine; the online policy is the reflex arc. The Markov-blanket separation between slow learning (offline) and fast acting (online) is the architecture of the brain itself, and is the right architecture here. Every mechanism, primary metaphor, archetype, and interaction in the live system was discovered or refined offline first. Without this pipeline, the platform's vocabulary is frozen at the moment of pilot launch.

**Implementation specification.**

- *Pipeline structure.*
  - Daily: ingest the prior day's `DecisionTrace`s and outcomes; produce a structured summary; feed to Claude API for hypothesis generation about which mechanisms underperformed/overperformed in which contexts; output is a list of candidate refinements to the online prior.
  - Weekly: run the full Bayesian causal-forest re-fit on accumulated `ConversionEdge` data; re-estimate heterogeneous treatment effects; re-fit the cross-category transferability matrix; reconcile with the online posteriors via warm-start.
  - Monthly: full corpus-level mechanism re-discovery — Claude API runs over a sampled slice of the Amazon review corpus (stratified by category) and proposes new mechanism atoms, new construct interactions, new primary metaphors. Knockoff filter applied to which proposed additions survive (FDR < 0.1).
  - Quarterly: full hierarchical reconciliation — corpus prior → category prior → brand prior → campaign prior, all re-fit.

- *Knockoff-filter FDR control.* For interaction selection (which entries of the trait × state × context tensor are non-zero), use the model-X knockoff filter (Candès et al. 2018). Robust at small N, doesn't require asymptotic approximations, controls FDR at user-specified level. This is the principled way to handle the multiple-comparisons problem in the interaction-discovery step.

- *Constitutional AI critic, repurposed.* The currently-built M6 cross-family critic (Opus critiques Sonnet) gets *repurposed* from the recommendation path (where it was theatre) into the offline mechanism-discovery pipeline (where it is genuinely useful). When Sonnet proposes a new mechanism atom or interaction, Opus critiques the proposal against the corpus evidence and the existing taxonomy. Genuine signal; no decision-time cost.

- *Brand Intelligence Library extension.* Existing Enhancement #14 extends to ingest LUXY-specific page-content corpus (LUXY website, blog, social, agency creative inventory, competitor positioning) and produce a per-brand primary-metaphor inventory. For LUXY: encode CONTAINMENT/CONTROL, RELIABILITY-AS-WEIGHT, FORWARD-MOTION/PROGRESS, STATUS-AS-VERTICALITY, TIME-AS-RESOURCE as the active inventory; offline pipeline surfaces additional candidates from the corpus.

- *Primary-metaphor compatibility scorer.* For each candidate (creative × page) pairing at decision time, score metaphor coherence between the brand's metaphor inventory and the page's evoked metaphor frame. Hard filter on low coherence (drops the candidate); soft input to the trilateral cascade for moderate coherence.

- *Precedent.* Enhancement #14 as the existing substrate; conceptual metaphor theory (Lakoff & Johnson; Grady on primary metaphors); knockoff filter (Barber & Candès 2015; Candès, Fan, Janson, Lv 2018).

### Spine #13 — Defensive Reasoning + Loop B + Mechanism-Rotation Demo Surface

**What it is.** The partner-facing surface that makes the entire architecture *legible* to the LUXY CMO and Becca. Three components:
1. Defensive Reasoning rendered from Spine #6 traces.
2. Loop B human-machine teaming (kAFC, RankOrder, SPIES, FourPoint, CounterExample, Scenario elicitation modes — the full set, finished).
3. Mechanism-rotation graph demo — live view of which mechanisms are firing for which audiences, with credible intervals, cohort drift indicators, and click-through to per-impression do-calculus traces.

**Why it's spine.** Without it, even a perfect inference engine is invisible. The pilot succeeds when the CMO can articulate, in his own words, what ADAM is doing differently — and that articulation depends entirely on the partner surface giving him the vocabulary and the inspectable artifacts.

**Implementation specification.**

- *Defensive Reasoning renderer.* Reads from `DecisionTrace`. Emits a structured why-view per impression with five layers:
  - One-line summary in primary-metaphor + posture vocabulary (e.g., "Served the FORWARD-MOTION creative because user is in TASK_COMPLETION posture on a productivity-tool page, with CONTAINMENT carryover from the prior touch already washed out.")
  - Counterfactual: "Would have served the RELIABILITY-AS-WEIGHT alternative, but the carryover penalty from yesterday's CONTAINMENT touch dropped its expected utility below the FORWARD-MOTION choice."
  - Contribution decomposition: bar chart showing how each scoring component (KL term, pragmatic, fluency, compatibility, carryover, epistemic) contributed to the score.
  - Confidence: 90% credible interval on the per-user effect of the chosen mechanism, with the cohort-pooled estimate alongside.
  - Provenance: links to the user's posterior history, the cohort's recent policy state, and the offline-discovered priors driving the decision.

- *Loop B elicitation UI.* Six elicitation modes:
  - **kAFC** (k-alternative forced choice — already shipped) — partner ranks creatives in a forced-choice paradigm against a context.
  - **RankOrder** (already shipped) — partner orders mechanisms by expected effectiveness for a cohort.
  - **SPIES** (Subjective Probability Interval Estimates) — partner provides an interval estimate for an effect; yields variance estimates needed for the precision-weighted active-inference layer.
  - **FourPoint** — partner provides four anchor points for a probability distribution; yields full distribution shape for prior elicitation.
  - **CounterExample** — partner provides counterexample cases ("here's a user who is in cohort X but I think mechanism Y won't work for them"); yields heterogeneous-effect priors.
  - **Scenario** — partner provides scenario descriptions; yields conditional priors (e.g., "in this situation, we'd expect this outcome").
  - All elicitations are bounded: any single elicited prior cannot exceed a posterior-weight floor that is a configurable fraction of the data-driven posterior. Partners can inject judgment but cannot override evidence.

- *Mechanism-rotation graph.* Live partner-facing dashboard showing:
  - Current mechanism allocation per cohort (stacked area over the past 7 days).
  - Posterior-credible-interval-width per mechanism per cohort (proxy for partner-narrative strength).
  - Cohort-drift indicators (Kalman-filter drift magnitude alerts).
  - Within-subject schedule for an exemplar user (clickable to see their history).
  - Sample of recent counterfactual-decision traces (clickable to drill into the do-calculus chain).
  - Attention-inversion floor compliance rate (target: 0.1–2% violation rate; an indicator outside this band flags a calibration problem).
  - mSPRT campaign monitor (Spine in Section 8; campaign-level "is ADAM better than holdout" boundary status).

- *Why this is the demo.* When the CMO walks through the mechanism-rotation graph and clicks into a trace, he sees: (a) the user-level N-of-1 inference, (b) the page-conditioned posture, (c) the carryover-aware crossover schedule, (d) the free-energy decomposition, (e) the counterfactual alternative, (f) the credible interval. That is the entire architecture, made visible. Nothing else in programmatic does this.

- *Precedent.* Enhancement #18 (Explanation Generation) provides the multi-audience explanation infrastructure; Enhancement #04 v3 metacognitive layer provides the reasoning-trace data structures.

---


---

## 3. The N-of-1 Substrate — Detailed Architectural Specification

This section deepens Spine #1 with the operational specification needed for Claude Code to begin implementing without further design. It is the single most important section of this directive after the opening frame.

### 3.1 The Frame

The N-of-1 substrate is the spine of the spine. Every other primitive in the cognitive architecture composes onto it. If it is not built correctly, every downstream claim — causal inference, attention-inversion compliance, decision-time counterfactuals, partner-facing explanations — fails silently. Build it as the foundation. Test it before anything is wired downstream.

### 3.2 Computational Architecture

Three execution paths, hierarchically composed:

**Path A — Online Conjugate Update (decision-time):**
- Called on every observation (impression, click, conversion, view-engagement, view-disengagement, frequency-fatigue).
- Per-user 27-dim Gaussian posterior; BONG single natural-gradient step in natural-parameter space (precision matrix + precision-weighted mean).
- Per-update cost: ~20K FLOPs at d=27 with full covariance, far less with diagonal-plus-low-rank.
- Storage: 729 floats per user (covariance + mean for full-cov), or ~80 floats per user (diagonal + low-rank-3 approximation).
- Hot cache (Redis): 1M most recently active users at full-cov = ~3GB. Acceptable.
- Latency target: <5ms for the update + <5ms for the read of relevant downstream consumers (cascade, free-energy scorer).

**Path B — Variational Batch Reconcile (nightly):**
- NumPyro SVI on the previous 24h of observations.
- Reconciles non-conjugate components (horseshoe interaction prior, AR(1) carryover coefficient, Kalman process-noise hyperprior).
- Produces the next day's online-update warm start.
- Runtime budget: ~1–2 hours nightly batch.

**Path C — HMC Offline Reconcile (weekly):**
- Full No-U-Turn-Sampler HMC on the past week's observations.
- Hierarchical-prior reconciliation (corpus → category → brand → campaign).
- Cross-validation of online posteriors against the slow-but-correct HMC posteriors.
- Drift-detection: if online and HMC posteriors diverge beyond a calibrated threshold, flag for investigation.
- Runtime budget: hours to days; not on any operational critical path.

### 3.3 Likelihood Specification

For user `i`, mechanism `a`, context `c`, time `t`, observed outcome `y_iat`:

```
y_iat | θ_i, β_a, γ_c, δ_iac, drift_t, carryover_t ~ Likelihood(η_iat)
η_iat = θ_i + β_a + γ_c + δ_iac + drift_t + carryover_t

θ_i ~ N(θ_cohort(i), Σ_θ)         partial pooling via cohort
β_a ~ N(μ_β, Σ_β)                  arm-specific shifts
γ_c ~ N(μ_γ, Σ_γ)                  context-specific shifts
δ_iac ~ Horseshoe(0, τ²)           sparse interactions, regularized
drift_t = drift_{t-1} + ε_drift    AR(1) state evolution
carryover_t = ρ_{m_{t-1} → m_t} · effect(m_{t-1}, t-Δ) · exp(-Δ / τ_{m_{t-1}})
```

Likelihood family depends on outcome class (Spine #11):
- `CONVERSION`, `MICRO_CONVERSION`: Bernoulli with positive update weight 1.0.
- `CLICK_QUALIFIED`, `VIEWED_ENGAGED`: Bernoulli with positive update weight 0.3–0.5 (partial credit).
- `CLICK_BOUNCED`, `VIEWED_DISENGAGED`: Bernoulli with negative update weight 0.5–1.0.
- `FREQUENCY_FATIGUE_FIRED`, `AUDIENCE_AGED_OUT`: censoring events; update the survival/competing-risks structure rather than the binary outcome.
- `IMPRESSION_NON_VIEWABLE`: discarded for posterior update (no signal); logged for accounting.

Outcome weights are themselves in a hyperprior; learned over time.

### 3.4 The Cohort-Membership-as-Posterior Object

Cohort assignment is *not* a hard partition. Each user has a posterior distribution over cohort membership, e.g., `[0.3, 0.5, 0.2]` over three cohorts. The user's prior at decision time is the mixture:

```
prior_user_i = sum_k P(cohort_k | i) · prior_cohort_k
```

This means a user with strong cohort-1 membership inherits cohort-1's mechanism priors heavily. As they accumulate observations, their cohort posterior updates AND their per-user posterior diverges from the cohort prior. New users start at the population prior; high-volume users converge to user-specific posteriors.

Identity-stability weight enters here: under cookie attrition or cross-device noise, the identity-stability weight `ω_i ∈ [0, 1]` modulates how much weight is given to the per-user posterior vs. the cohort prior:

```
effective_prior_i = ω_i · per_user_posterior_i + (1 − ω_i) · cohort_mixture_prior_i
```

Identity-stability weight is itself a learned object: how often does this user's identity persist across sessions? This degrades smoothly under privacy-conscious deployment.

### 3.5 Action Selection at Decision Time

Top-two Thompson Sampling (TTTS) with epistemic-value bonus and free-energy modulation:

```
For each candidate mechanism a in eligible_set(user, context, schedule):
    posterior_score(a) = sample_from_posterior(p_iat | observations)
    free_energy(a) = compute_F(a | user_state, page_posture)   # Spine #5
    fluency(a) = compute_fluency(creative_a, page_context)     # Spine #4
    if fluency(a) < FLUENCY_FLOOR:
        remove a from eligible_set                              # hard floor
        continue
    epistemic(a) = compute_epistemic_value(a | user_posterior) # Spine #8
    
    final_score(a) = posterior_score(a) − λ_F · free_energy(a) + λ_E · epistemic(a)

chosen = top_two_thompson_sample(final_scores)
```

Notes:
- `λ_F` and `λ_E` are policy hyperparameters; defaults tuned in offline simulation.
- TTTS is preferred over vanilla Thompson sampling for best-arm identification at fixed N; closed-form propensity (Jeunen 2025) enables propensity logging for off-policy evaluation (Spine #6).
- The "eligible set" is determined by the within-subject scheduler (Spine #2), the fluency floor (Spine #4), and the cohort-conditional policy (Spine #7). Action selection operates only over the eligible set.

### 3.6 Storage Architecture

- **Neo4j:** `UserPosterior` nodes, one per active user, with the full hierarchical posterior structure (precision matrix, mean vector, cohort-membership vector, identity-stability weight, last-update timestamp, total observations). `ConversionEdge` nodes link users to mechanisms via outcome events. `DecisionTrace` nodes capture per-impression provenance.
- **Redis:** Hot cache of the most recently touched user posteriors. Compressed representation (diagonal + low-rank or PCA-projected). Sub-5ms read latency.
- **Object store (S3 or equivalent):** Long-term archival of decision traces, nightly batch reconcile outputs, weekly HMC posteriors. Compressed parquet format; indexed by user_id and timestamp.

### 3.7 Integration with StackAdapt's Inbound-Only Data Plane

StackAdapt does not support outbound conversion webhooks for creative selection. The integration is architecturally inverted; the substrate must accommodate this.

**Outbound (ADAM → StackAdapt):**
- Audience segment pushes via GraphQL API. Each cohort is a StackAdapt audience; users move between audiences as cohort posteriors update. Sync cadence: hourly is sufficient; daily is acceptable.
- CRM upload for first-party-data-augmented audiences (LiveRamp/RampID match window: ~30 minutes).
- Creative variants uploaded via `createCreativeByURL()` GraphQL mutation, tagged with mechanism metadata.
- Pixel API for inbound conversion / qualifying events, server-to-server.

**Inbound (StackAdapt/LUXY → ADAM):**
- URL macro `sapid={SA_POSTBACK_ID}` on landing-page click URLs, captured server-side. This is the *only* deterministic linkage between a served impression and a downstream observation; treat it as sacred.
- Pixel events keyed by `sapid` plus IP/user-agent fallback for view-through.
- Reverse ETL of past impressions back into the substrate for cold-start initialization.
- Daily reporting via GraphQL for impression-level data.

**The sapid round-trip.** This is operationally fragile. Implement end-to-end before anything else in the substrate ships. Without it, the engine has no signal channel. Specifically:
1. ADAM-uploaded creatives carry landing-page URLs with a `sapid={SA_POSTBACK_ID}` macro.
2. StackAdapt fills in the macro at impression-bid time.
3. User clicks → lands on LUXY page → LUXY page captures `sapid` server-side at first byte (not via JavaScript, which is fragile to ad-blockers and CSPs).
4. LUXY conversion server fires the StackAdapt Pixel API with the captured `sapid`.
5. ADAM pulls conversion data via GraphQL with `sapid` as the join key.
6. Round-trip rate is monitored as a load-bearing operational metric (target: ≥98% of conversions back-linked to served impressions).

### 3.8 Surviving Small-Sample Reality

At the LUXY pilot's expected volumes (~30–600 conversions/week depending on assumptions), traditional power calculations require months. The substrate's small-sample survival mechanisms:

1. **Hierarchical pooling** — per-user effects shrink toward cohort means; cohort means shrink toward grand mean. Reduces effective parameter count from O(users × arms) to O(cohorts × arms). Standard partial-pooling theory.

2. **Sequential probability ratio test (SPRT) per user, per arm** — Wald's optimal sequential test minimizes expected sample size to a decision. Use mSPRT (mixture SPRT) for the population-level "is this campaign creating lift" question; it permits continuous monitoring without alpha inflation.

3. **Off-policy evaluation via the counterfactual trace (Spine #6)** — every served impression scores every arm. ~3–5x effective sample size multiplier under TTTS.

4. **Negative outcomes counted explicitly (Spine #11)** — broader outcome vocabulary, denser signal. ~10–100x more abundant than positives.

5. **Conformal ITE intervals** — distribution-free, valid at any sample size, give the partner-facing uncertainty story without needing CLT-style asymptotics. Use weighted conformal prediction for time-varying coverage (Bose-Dempsey 2025 multi-decision-point extension).

6. **Knockoff filter for false-discovery control on which trait × state × context interactions are real** — robust at small N, doesn't require asymptotic approximations.

### 3.9 What This Substrate Is NOT

- It is NOT "personalization" in the industry sense. Personalization is variant matching to user features. N-of-1 is causal-identification within-subject.
- It is NOT "frequency capping." Frequency capping is a max-count rule. N-of-1 scheduling is a *design* with washouts, sequences, and replications.
- It is NOT "A/B testing per user." A/B per user is undisciplined. N-of-1 has pre-specified sequences, washouts, replication, and a likelihood model with carryover.
- It is NOT a conformal-CATE substitute. Population CATE is a different estimand. N-of-1 is the per-user analog; aggregating per-user posteriors yields a different (and more honest, at this sample size) population estimate than direct CATE estimation.

---

## 4. The Bilateral Cascade and Trilateral Page Conditioning

This section deepens Spine #4 with the operational specification for the trilateral cascade and the architectural enforcement of attention-inversion.

### 4.1 The Cascade Structure

Existing Enhancement #14 / #28 architecture provides a bilateral 5-level cascade:
- **L1 archetype prior** — pre-computed intelligence profiles for each archetype.
- **L2 category posterior** — category-conditioned mechanism distributions.
- **L3 bilateral edges** — user × creative-mechanism matched evidence.
- **L4 inferential transfer** — cross-category transferability.
- **L5 mechanism synergy / antagonism check** — synergy pairs amplified, antagonism pairs swapped.

The L3 trilateral extension adds page-attentional-posture as a first-class third dimension at the L3 layer.

### 4.2 The Page Attentional-Posture Encoder

**Architecture:**
- Frozen sentence-transformer (`all-mpnet-base-v2` initially; consider domain-tuning to corporate-travel-adjacent corpora later).
- Posture head: 5-class classifier on top of the 768-dim embedding.
- Auxiliary regression heads:
  - Cognitive load / processing-depth (continuous 0–1).
  - Emotional valence (−1 to 1).
  - Arousal level (0–1).
  - Information density (0–1).
  - Goal-pursuit clarity (0–1; how much the page primes a clear goal vs. ambiguous browsing).

**Training data:**
- 300–500 hand-labeled exemplar URLs from LUXY-plausible inventory (corporate-travel sites, business news, premium publishers, productivity tools, expense-management tools).
- Active-learning loop: posture classifier flags low-confidence pages; offline pipeline (Claude API) labels them; classifier retrains.

**Calibration:**
- Posture confidence: 0–1, used to weight the posture's influence on the cascade.
- Low-confidence pages fall back to category-prior-only scoring with no posture conditioning.

### 4.3 The Posture × Mechanism Compatibility Prior

For each `(posture, mechanism)` pair, an initial compatibility score in `[-1, +1]`:
- `+1`: highly fluent (mechanism naturally fulfills the goal the posture is in).
- `0`: neutral (mechanism is neither aided nor hindered).
- `-1`: incompatible (mechanism fights the posture).

Examples (illustrative; the actual matrix is filled by the offline pipeline):
- LOSS_AVERSION × INFORMATION_FORAGING: ~0.0 (information-foraging is neutral to loss framing; depends on what's being foraged).
- LOSS_AVERSION × LEISURE_BROWSING: ~-0.3 (loss framing intrudes on leisure mode; mild reactance risk).
- CONSTRUAL_LEVEL_CONCRETE × INFORMATION_FORAGING: ~+0.7 (concrete information aligns with research mode).
- IDENTITY_CONSTRUCTION × SOCIAL_CONSUMPTION: ~+0.5 (identity-expressive content is congruent with social posture).
- AUTHORITY_EVOCATION × TASK_COMPLETION on productivity tool: ~+0.4 (authority cues fit professional task posture).
- WANTING_LIKING × TASK_COMPLETION on expense management: ~-0.5 (hedonic appeal fights utilitarian task).
- ATTENTION_DYNAMICS × SOCIAL_CONSUMPTION: ~-0.6 (attention-grabbing creative is *exactly* what social-consumption mode is fatigued from).

The matrix is updated by online observations; the campaign-level posterior on `compatibility(posture, mechanism)` is part of the bilateral edge structure.

### 4.4 The Fluency Floor — Hard Architectural Constraint

For each candidate creative `a` against page context `c`:
- Fluency-against-context score: `fluency(a, c) ∈ [0, 1]`, derived from the embedding cosine similarity between creative's metaphor + mechanism profile and the page's posture + content profile, weighted by posture confidence.
- If `fluency(a, c) < FLUENCY_FLOOR`: the candidate is *removed* from the eligible set. Period. No epistemic bonus, no exploitation pressure, no override.

Floor calibration:
- Calibrate against a held-out set of manually labeled "this is grabby / this is blendy" page-creative pairs (50–100 pairs initially; grow during pilot).
- Target violation rate: 0.5–2% of decisions. Below 0.1% means the floor is too lax (let grabby creative through); above 5% means the floor is too strict (the system can't find eligible candidates).

This is the architectural enforcement of attention-inversion. Foundation §7 rule 11 made operational.

### 4.5 Decision-Time Latency Budget

Three tiers, total latency target <100ms:

**Tier 1 — Warm cache (target <30ms):**
- Page posture cached (URL hit).
- User posterior cached (active user).
- Bilateral edge priors cached (recent campaign data).
- Compatibility priors cached.
- Cascade scoring runs in-memory.
- Action selection via TTTS, propensity logging, decision trace emission.

**Tier 2 — Live posture inference + Neo4j 2-hop (target <100ms):**
- Posture cache miss → live encoding (10–20ms for sentence-transformer).
- User posterior cache miss → Neo4j load + Redis backfill (10–30ms).
- Live bilateral edge query (2-hop Cypher with archetype filter): 10–30ms.
- Cascade scoring + decision: 10–20ms.

**Tier 3 — Cold cache + Claude reasoning (NOT on bid-time critical path):**
- For novel page-creative-context combinations, Claude API generates new candidate creatives or new bilateral-edge interpretations.
- Pre-computed during offline pipeline; never blocks bid response.

---

## 5. The Decision-Time Intelligence Layer (Bringing It All Together)

This section consolidates Spines #5, #6, #7, #8, #9 into the unified decision-time policy.

### 5.1 The Full Decision Pipeline

For each incoming bid request:

1. **Identity resolution** (1–3ms): hashed identity / cookie / device-graph. Identity-stability weight `ω_i` computed.
2. **User posterior load** (Tier 1: <5ms; Tier 2: 10–30ms): full hierarchical posterior + cohort membership.
3. **Page posture load** (Tier 1: <5ms; Tier 2: 10–20ms live).
4. **Within-subject schedule check** (Spine #2): which mechanisms are eligible for this user right now (washout-respecting, sequence-respecting).
5. **Eligible-set construction**: schedule-eligible mechanisms × ad inventory → candidate set.
6. **Fluency floor filter** (Spine #4): drop candidates below floor.
7. **Cascade scoring** (Spine #4): trilateral score per remaining candidate.
8. **Free-energy modulation** (Spine #5): `score → score − λ_F · F`.
9. **Epistemic-value bonus** (Spine #8): `score → score + λ_E · epistemic`, conditioned on fluency-floor pass.
10. **Carryover correction** (Spine #2): `score → score − carryover_penalty`.
11. **Top-two Thompson sample** (Spine #1, #6): chosen mechanism + propensity logged.
12. **Kelly-fraction bid sizing** (Spine #9): `bid = quarter_kelly(posterior_edge, auction_clearing_estimate) − winner_curse_shading`.
13. **Decision trace emission** (Spine #6): full structured trace persisted to Redis (hot) and Neo4j (long-term).
14. **Bid response** to StackAdapt within latency budget.

### 5.2 Outcome Update Pipeline

When an outcome event arrives (any of the Spine #11 outcome classes):

1. **Identify the originating decision** via `sapid` linkage.
2. **Outcome class classification** (Spine #11 vocabulary).
3. **Update weight selection** based on outcome class.
4. **BONG natural-gradient update** on the user posterior (Spine #1).
5. **Cohort-prior update** with appropriate hierarchical weight (Spine #1, #7).
6. **Carryover-coefficient update** (Spine #2).
7. **Bilateral-edge update** in Neo4j (Spine #3).
8. **Decision-trace closure**: link the trace to the outcome.
9. **Off-policy evaluator update** (Spine #6): update the IPS / DR / SNIPS estimates for *every* arm, using the logged propensities.

This is the learning loop. Sub-100ms updates per observation; nightly batch reconcile; weekly HMC reconcile.

### 5.3 Pacing and Budget Allocation

- Restless-bandit Whittle-index allocation across cohorts (Spine #7).
- Quarter-Kelly fractional pacing within cohorts (Spine #9).
- Mortal-bandit treatment of expiring creatives (Spine #7).
- Epistemic-bonus capped as a fraction of total cohort budget per day.
- Holdout (deterministic-hash, 5–10% of bid-eligible traffic) untouched.

### 5.4 Cross-Mechanism Synergy / Antagonism Check

Existing Enhancement-system L5 synergy check is already wired. It runs against the warm cache (CognitiveMechanism nodes pre-loaded). When the cascade recommends mechanism A primary + mechanism B secondary, the synergy check verifies that (A, B) is not in the antagonism set; if it is, B is swapped for the next-best candidate.

This integrates with Spine #2: the within-subject scheduler already enforces washout for individual mechanisms; the synergy check enforces same-impression compatibility for primary/secondary mechanism pairs.

---

## 6. The Offline Learning Engine — Claude API as the Slow Brain

### 6.1 The Markov-Blanket Architecture

The brain's separation of slow learning (cortex; reflective; expensive; rare) from fast acting (subcortex; reflexive; cheap; constant) is the right architecture for ADAM. The online pipeline is the reflex arc; the offline pipeline is the slow-learning brain. Never confuse them in latency budget or in persistence.

**Online pipeline:**
- Latency budget: <100ms per decision.
- Persistence: per-decision trace, per-observation update.
- Reasoning depth: shallow, cached, deterministic where possible.
- LLM use: zero (or pre-computed). Claude API is *never* on the bid-time critical path.

**Offline pipeline:**
- Latency budget: hours to weeks.
- Persistence: hierarchical priors, brand intelligence, mechanism taxonomy, primary-metaphor inventory, interaction tensor sparsity pattern.
- Reasoning depth: full Claude API capability.
- Output: priors, taxonomies, hypotheses, interpretations, refinements — all of which flow to the online pipeline as updated parameters.

### 6.2 The Pipeline Stages

**Daily:**
- Ingest prior 24h `DecisionTrace`s and outcomes.
- Stratified-sample summary (which mechanisms underperformed vs. which overperformed, in which contexts, for which cohorts).
- Claude API runs hypothesis generation: "given these underperformance patterns, what mechanism refinements should we propose?"
- Output: candidate refinements to online priors. Not auto-applied; queued for human review (Loop B partner-side, internal review on the engineering side).
- Brand Intelligence Library updates from any new LUXY page-content seen.

**Weekly:**
- Bayesian Causal Forest re-fit on accumulated `ConversionEdge` data.
- Cross-category transferability matrix re-fit.
- Knockoff-filter FDR control on which interactions in the trait × state × context tensor are non-zero (control at 0.1).
- HMC reconcile of online posteriors vs. slow-but-correct.
- Cohort-discovery HMM re-fit (Spine #7); cohort definitions updated.

**Monthly:**
- Full corpus-level mechanism re-discovery.
- Claude API runs over a stratified slice of the Amazon corpus (not the full 1.2B; sampled for tractability).
- Proposes new mechanism atoms, new construct interactions, new primary metaphors.
- Knockoff-filtered.
- Constitutional-AI critic (M6, repurposed): Opus critiques Sonnet's proposals against corpus evidence and existing taxonomy.
- Surviving proposals enter the candidate-mechanism pool, gated for human approval before promotion to active use.

**Quarterly:**
- Full hierarchical-prior reconciliation: corpus → category → brand → campaign.
- Audit of the brand-intelligence library against current LUXY-corpus-derived state.
- Audit of primary-metaphor inventory against the page corpus and the live decision traces.

### 6.3 Brand Intelligence Library — LUXY Specification

Existing Enhancement #14 already provides the substrate. For LUXY, the offline pipeline ingests:

- LUXY website content (luxyride.com — corporate site, blog, press, case studies).
- LUXY social presence (LinkedIn primarily; this is B2B corporate-travel).
- Existing creative inventory (the agency's current LUXY ads).
- Competitor positioning (Blacklane, Carey, Boston Coach, Empire CLS).
- Customer testimonials, case studies, third-party reviews.
- Concur / TripActions / TMC integration documentation (for understanding the buyer-side context).

Outputs:
- Primary-metaphor inventory for LUXY (initial: CONTAINMENT/CONTROL, RELIABILITY-AS-WEIGHT, FORWARD-MOTION/PROGRESS, STATUS-AS-VERTICALITY, TIME-AS-RESOURCE; offline pipeline expands).
- Brand-side construct annotation across all 27 dimensions (regulatory focus, construal level, moral foundations, sensation seeking dimension, etc.).
- Customer archetype inventory (initial: STATUS_SEEKER, CAREFUL_TRUSTER, EASY_DECIDER as the active targets; SKEPTICAL_ANALYST and DISILLUSIONED as suppressions; offline pipeline refines).
- Per-archetype creative-direction templates: which mechanisms align with which archetypes for LUXY specifically.
- Goal-state inventory: what goals do LUXY customers come into LUXY-relevant contexts pursuing (commute-readiness, expense-control, time-recovery, status-display, professional-encounter-preparation, anxiety-reduction, etc.).

### 6.4 Primary-Metaphor-Driven Generation

For each new creative variant ADAM proposes:

- Conditioned on a target primary metaphor + a target mechanism + a target goal state + a target posture.
- Claude API generates the variant under the constraint: "produce a variant that activates [primary metaphor] via [mechanism] for a user in [posture] pursuing [goal state]."
- Generated variants are scored against:
  - Primary-metaphor coherence with the target.
  - Mechanism-activation strength.
  - Predicted fluency against representative pages of the target posture.
  - Predicted reactance risk (independently scored — see below).
- Variants below thresholds are rejected; surviving variants enter the candidate pool.
- New variants are uploaded to StackAdapt via `createCreativeByURL()` with mechanism + metaphor + posture metadata.

### 6.5 Reactance Risk Independent Scoring

In addition to fluency floor (Spine #4), every generated creative is scored independently for reactance risk:
- Persuasion-intensity / explicitness markers ("only," "must," "limited time," "act now," urgency cues).
- Pressure-language density.
- Override-of-user-control cues (countdown timers, scarcity claims, social-proof manipulation).
- Reactance score is one of the dimensions that the BCF heterogeneous-effects model can identify as a moderator: high-reactance users + high-pressure ad → negative effect.

Above a threshold reactance score, the creative is rejected at offline-pipeline time and never enters the live candidate pool. This is a second architectural defense (alongside the fluency floor) of the attention-inversion principle.

---

## 7. The Partner Surface — Loop B and the Demo

This section deepens Spine #13.

### 7.1 The Two-View Dashboard

The agency and the CMO need exactly two primary views; everything else is supporting:

**View A — Mechanism rotation graph.**
- X-axis: time (rolling 30-day window).
- Y-axis: budget allocation per cohort.
- Stacked area: which mechanisms are firing for each cohort.
- Annotations:
  - Cohort posterior intervals.
  - Cohort-drift indicators (Kalman flag).
  - Within-subject schedule for an exemplar user (toggle).
  - mSPRT campaign-level boundary status.
  - Attention-inversion floor compliance rate (color-coded indicator).
- Interaction: click a point → drill into the per-cohort policy state at that time.
- Click a user trajectory → see their full N-of-1 history (within-subject design, schedule, observations, posterior evolution).
- Click an impression → see the do-calculus chain (Defensive Reasoning panel).

**View B — Loop B elicitation surface.**
- Six elicitation modes (kAFC, RankOrder, SPIES, FourPoint, CounterExample, Scenario).
- Per-mode UI: matched to the cognitive-task structure of the elicitation.
- Outputs flow into the hierarchical-prior structure (Spine #1, Spine #3) as bounded prior adjustments.
- Visualization of which past elicitations are currently informing which decisions.

### 7.2 The Defensive Reasoning Panel

Triggered by clicking any impression in View A. Reads from the `DecisionTrace` (Spine #6).

Five layers, rendered top-down for the partner:

1. **Plain-language one-liner.** "Served the FORWARD-MOTION creative because user is in TASK_COMPLETION posture on a productivity-tool page, with CONTAINMENT carryover from yesterday's touch already washed out. Expected utility 0.067; runner-up RELIABILITY-AS-WEIGHT at 0.041."
2. **Counterfactual.** "Would have served RELIABILITY-AS-WEIGHT, but the carryover penalty from yesterday's CONTAINMENT touch dropped its expected utility below FORWARD-MOTION."
3. **Decomposition bar chart.** Each scoring component (KL term, pragmatic, fluency, compatibility, carryover, epistemic) as a contribution percentage.
4. **Confidence.** 90% credible interval on the per-user effect of the chosen mechanism. Cohort-pooled estimate alongside.
5. **Provenance.** Links to the user's posterior history; the cohort's recent policy state; the offline-discovered priors driving the decision; the original elicitation (if any) that shaped the prior.

### 7.3 The Walkthrough

The CMO walkthrough is the partner-facing version of the demo. The script:

1. Show View A.
2. Point out the mechanism-rotation pattern: which mechanisms are firing for which cohorts.
3. Pick a cohort that's drifting; show the Kalman-flag and the cohort-drift annotation; explain that the system is updating the cohort policy as the population shifts.
4. Click into an exemplar user; show the within-subject schedule (ABAB, washout, replication structure).
5. Click into a single impression; show the Defensive Reasoning panel.
6. Walk through the do-calculus chain.
7. Show the counterfactual: "this is what would have happened with the runner-up."
8. Show the credible interval: "this is what we know about this user, with appropriate humility."
9. Show the attention-inversion compliance metric: "this is the architectural floor we never violate; here's the rate we're at."
10. Show the mSPRT board: "this is the campaign-level question we're tracking; here's where we are."

If the CMO can articulate, in his own words, what just happened, the partner surface has done its job.

---

## 8. The Honest Measurement Layer

This section enumerates what stays, what gets cut, and what is replaced.

### 8.1 What Gets Cut From the Existing Roadmap

Stated bluntly so there is no ambiguity:

- **C3 Calibration Journal (per-user-per-domain Brier scores).** Cut. Per-user Brier is below noise floor at pilot N. Replaced by per-user posterior credible intervals and cohort-level posterior decomposition (which is what calibration *should* mean here).
- **B4 Plant model + adjudicator extension (synthetic-lift planting).** Cut. QA theatre. Replaced by the simulation exercise (Section 11) for offline validation.
- **B5 Weakness #6 distribution-calibrated thresholds.** Cut. Bayesian posterior cutoffs replace frequentist thresholds throughout.
- **C5 Protocol Meta-Learner.** Cut from pilot. Premature; presupposes a protocol portfolio that doesn't exist yet.
- **A14 retirement-trigger public dashboard.** Cut from pilot launch path. Revisit as a compliance/audit feature post-launch.
- **Per-archetype lift heterogeneity reporting.** Cut. Replaced by the trait × state × context interaction model itself (Spine #1's δ_iac), which decides rather than reports.
- **Per-cell sample-size adequacy tracker.** Cut. SPRT and conformal intervals replace sample-size threshold logic.
- **HumanDeviation lifecycle (C4) — full adjudication pipeline.** Reduce to log-and-tag. Cut the verdict machinery.
- **M6 Cross-family Constitutional AI critic in the recommendation path.** Cut from serving path. Repurposed for offline mechanism-discovery (Section 6).

Estimated reclaim: 30–45% of engineering hours that were going to measurement infrastructure. Those hours fund the spine.

### 8.2 What Stays From the Existing Build

- **A1–A5 cascade wirings.** All keep — they are the substrate for the spine primitives. Promote A4 (page attentional posture) from helper to first-class.
- **C1 v0.2 elicitation (kAFC + RankOrder).** Keep; finish C1 to all six modes (Section 7.1).
- **C2 Why Library closed-vocabulary tags.** Keep, narrow scope; populated from `DecisionTrace` not from a separate taxonomy.
- **Defensive Reasoning at recommendation time.** Keep; reframe to read from `DecisionTrace`.
- **2,465 unit tests + 162 net-new this week.** Keep. Future tests should be on cognitive primitives.

### 8.3 What Replaces the Cut Items

- **Per-user posterior credible intervals** (Spine #1) replace per-user Brier journal.
- **Bayesian posterior cutoffs** replace distribution-calibrated thresholds.
- **Trait × state × context interaction model** (Spine #1's δ_iac with horseshoe priors) replaces per-archetype lift heterogeneity reporting.
- **mSPRT campaign-level monitor** replaces sample-size adequacy tracker for the campaign-level question.
- **Conformal ITE intervals** (Bose-Dempsey 2025) replace M2's split-conformal lift wrap as the per-user uncertainty-quantification layer.
- **Knockoff-filter FDR control** on interaction selection (Spine #12) replaces uncorrected lift-heterogeneity reporting.
- **Deterministic-hash holdout** (5–10% of bid-eligible traffic, untouched) replaces holdout-discipline runtime enforcement scaffolding.
- **Pre-registered campaign-level Bayesian comparison** replaces the M2/B1 calibration pipeline as the population-level estimand.

### 8.4 The Pre-Registered Population-Level Analysis

Before launch, lock the population-level analysis:
- Estimand: ATE on conversion rate (ADAM-treated vs. holdout) over the pilot window.
- Prior: weak Gaussian on the difference, centered at 0.
- Likelihood: Bernoulli on conversion / outcome composite per user-day.
- Posterior: Gaussian process over the daily-difference time series (handles autocorrelation).
- Reporting: posterior probability of positive lift; 95% credible interval on lift; per-cohort posteriors with appropriate hierarchical pooling.
- mSPRT boundaries: pre-specified; crossing the upper boundary mid-pilot is a positive signal for Becca to share internally; crossing the lower boundary is a RED-criterion launch deferral trigger.
- Per-user analyses (the within-subject contrasts) are *exhibit*, not *estimand*; they are the demonstrable claim that nobody else can make at this scale, but the campaign-level estimand is the formal lift result.

---

## 9. The Build Sequence

No calendar. Phase-by-phase. Each phase has explicit dependencies, deliverables, and gates.

### Phase 1 — Substrate Foundation

**Dependencies:** None.

**Deliverables:**
- Cut bias-leak items (Section 8.1) from the build queue. Quarantine code that may be useful later (M2 calibration, M6 critic, B4 plant model); delete code that is purely dead weight.
- Implement Spine #1 (per-user N-of-1 hierarchical Bayesian engine) in NumPyro/JAX:
  - BONG online conjugate update path.
  - Variational batch reconcile path.
  - HMC offline reconcile path.
  - Storage schema in Neo4j (`UserPosterior` node), Redis hot cache.
  - Pydantic models for posterior snapshots.
- Implement Spine #2 (within-subject scheduler with washout and carryover):
  - Schedule generator (ABAB, RAR, SMART).
  - Washout-interval table (mechanism-specific half-lives, initialized informatively).
  - AR(1) carryover correction in the N-of-1 likelihood.
- Implement Spine #11 (LUXY negative-outcome adapter) end-to-end:
  - Outcome vocabulary classes.
  - Pixel handler client + server.
  - sapid round-trip implementation.
  - Likelihood-weight schema for each outcome class.

**Gate:** End-to-end synthetic trajectory test. A simulated user receives 8 touches across 2 mechanisms with washout, and the system produces (a) coherent posterior trajectory, (b) within-subject crossover with carryover correction visible, (c) explicit non-response handling, (d) all storage paths exercised. RED if any of (a)–(d) fails.

### Phase 2 — Page Conditioning and Trilateral Cascade

**Dependencies:** Phase 1.

**Deliverables:**
- Page attentional-posture encoder (Spine #4, Section 4.2):
  - Frozen sentence-transformer.
  - Five-class posture head trained on 300–500 hand-labeled URLs.
  - Auxiliary regression heads.
  - Active-learning loop wired to offline pipeline.
- Posture × mechanism compatibility prior matrix.
- Trilateral L3 cascade scoring function in `bilateral_cascade.py`:
  - Promote A4 page_attentional_posture from helper to first-class conditioning variable.
  - Replace bilateral cascade with trilateral wherever it is consumed.
- Fluency floor implementation (hard constraint, not optimization term):
  - Calibrate threshold against held-out labeled set (50–100 page-creative pairs).
  - Wire as eligibility filter, not as score modifier.

**Gate:** Floor calibration in 0.5–2% violation range against the held-out set. Trilateral cascade produces qualitatively different scores for the same (user, creative) pair across different posture classes (sanity check: scoring should not be posture-invariant). RED if floor cannot calibrate, or if posture has no observable effect on scoring.

### Phase 3 — Mechanism Interaction and Cohort Discovery

**Dependencies:** Phase 1, Phase 2.

**Deliverables:**
- Trait × state × context interaction tensor (Spine #1's δ_iac):
  - Horseshoe prior implementation.
  - Pre-specified interaction list (~10–15 interactions Chris believes exist).
  - Knockoff-filter FDR control on which interactions are non-zero.
- Cohort discovery via HMM-over-behavior (Spine #7):
  - 6–10 cohorts.
  - Initialization from Loop B elicitations.
  - Posterior cohort-membership per user (not hard partition).
- Cohort-conditional non-stationary policy:
  - Discounted-TS / SW-UCB per cohort.
  - Restless-bandit Whittle-index allocation across cohorts.
  - Mortal-bandit creative-fatigue treatment.
- Online Kalman-filter state-space personalization (Spine #10) wrapping Spine #1.

**Gate:** Synthetic non-stationary trajectory: a simulated cohort experiences an abrupt regime shift; the system's lift-recovery time after the shift is materially better than a static-priors baseline. RED if recovery time is not improved.

### Phase 4 — Decision-Time Intelligence Layer

**Dependencies:** Phases 1–3.

**Deliverables:**
- Active-inference free-energy scorer (Spine #5):
  - Goal-state inventory definition (12–15 goal states).
  - Generative model for `q(goal_state | a, s, c)` and `p(goal_state | s, c)`.
  - Free-energy decomposition into KL term and pragmatic term.
  - Integration with action selection as soft objective.
- Decision-time counterfactual trace (Spine #6):
  - Pydantic `DecisionTrace` schema.
  - Top-two Thompson sampling propensity logging (Jeunen 2025 closed-form).
  - Off-policy evaluator (IPS, Doubly Robust, SNIPS).
  - Storage in Redis (hot) + Neo4j (long-term).
- Active-inference epistemic-value bid bonus (Spine #8):
  - Closed-form information gain under BONG.
  - Decay-with-precision weighting.
  - Cap as fraction of cohort daily budget.
  - Conditioned on fluency-floor pass.
- Kelly-fraction bid sizing (Spine #9):
  - Quarter-Kelly default with calibration.
  - Winner's-curse shading per supply path.
  - Pacing-modifier integration.
- Mechanism synergy/antagonism check (existing L5) integrated with the trilateral cascade.

**Gate:** End-to-end decision pipeline executes within latency budget on a backtest of realistic LUXY-flavored synthetic week (3.75M imps, 80–150 conversions). System bids on >70% of eligible auctions, violates fluency floor on <2% of decisions, produces a counterfactual trace for 100% of bids, reaches defensible per-user posterior on simulated heavy-touch users. RED if any fails.

### Phase 5 — Bilateral Causal Edge and Cross-Category Transfer

**Dependencies:** Phases 1–4.

**Deliverables:**
- Bilateral causal-edge architecture finalization (Spine #3):
  - DoWhy + EconML AIPW pipeline.
  - Bayesian Causal Forest with shrinkage / horseshoe priors.
  - Refutation tests (placebo, dummy outcome, random common cause).
  - `is_causal` boolean wired throughout.
  - Helpful-confidence multiplier on review evidence.
- Hierarchical prior pipeline (corpus → category → brand → campaign):
  - LUXY brand-prior layer initialization from Beauty & Personal Care category transfer.
  - Per-dimension transferability matrix applied.
  - First-week-of-pilot observations begin updating brand-prior layer.

**Gate:** Bilateral edge query latency in target range; transferred priors produce non-degenerate scoring on LUXY-relevant test cases; refutation tests pass on the synthetic-data validation cases. RED if causal-effect estimates are statistically indistinguishable from null on synthetic ground-truth cases.

### Phase 6 — Offline Learning Engine and Brand Intelligence

**Dependencies:** Phases 1–5.

**Deliverables:**
- Offline pipeline (Spine #12):
  - Daily, weekly, monthly, quarterly cadences as specified in Section 6.2.
  - Claude API integration with structured output for hypothesis generation.
  - Knockoff-filter FDR control wired.
  - M6 Constitutional AI critic *repurposed* into offline mechanism-discovery (no longer in serving path).
- Brand Intelligence Library — LUXY specification (Section 6.3):
  - Full LUXY corpus ingest.
  - Primary-metaphor inventory (initial five + offline-pipeline expansion).
  - Per-archetype creative-direction templates.
  - Goal-state inventory.
- Primary-metaphor-driven creative generation (Section 6.4):
  - Conditioned generation via Claude API.
  - Multi-dimensional scoring (metaphor coherence, mechanism activation, predicted fluency, reactance risk).
  - Threshold-based rejection.
  - Upload to StackAdapt with metadata.
- Reactance-risk independent scorer (Section 6.5).

**Gate:** Generated creative variants pass internal review for primary-metaphor coherence and reactance compliance at >80% rate; offline pipeline produces non-trivial daily summaries that surface real underperformance patterns when run on synthetic decision-trace data. RED if generated creative repeatedly violates Foundation §7 rule 11 in qualitative review.

### Phase 7 — Partner Surface

**Dependencies:** Phases 1–6.

**Deliverables:**
- Defensive Reasoning renderer (Section 7.2):
  - Reads from `DecisionTrace`.
  - Five layers populated correctly.
- Loop B elicitation UI — full six modes (Section 7.1):
  - kAFC + RankOrder (already shipped, verify integration).
  - SPIES, FourPoint, CounterExample, Scenario (new).
  - All elicitations bounded; configurable posterior-weight floor.
- Mechanism-rotation graph (View A):
  - Stacked area, cohort overlays, drift indicators.
  - Click-through to user trajectories and decision traces.
  - Live attention-inversion floor compliance metric.
  - mSPRT campaign monitor.
- CMO walkthrough script (Section 7.3) — internal rehearsal version.

**Gate:** Internal red-team review of the partner surface: a non-engineer is able to navigate from "what's happening" to a specific impression's do-calculus chain in <5 clicks. RED if the demo cannot be navigated without showing a measurement-theatre artifact you forgot to remove. RED if any path through the demo reveals a grabby creative slipping past the fluency floor.

### Phase 8 — StackAdapt Integration Hardening

**Dependencies:** Phases 1–7.

**Deliverables:**
- StackAdapt GraphQL write-API integration (when available; otherwise agency-handoff cycle):
  - Audience push pipeline (cohort → StackAdapt audience sync).
  - Creative upload pipeline (`createCreativeByURL()` with full mechanism + metaphor + posture metadata).
  - Daily reporting pull.
  - Pixel API for inbound conversions.
- sapid round-trip end-to-end monitoring.
- Holdout-discipline single-function deterministic-hash implementation (5–10% of bid-eligible traffic, untouched).

**Gate:** Round-trip rate on synthetic-flow test ≥98%. Identity-stability weight degrades smoothly under simulated cookie attrition. RED if signal channel is fragile under realistic operational conditions.

### Phase 9 — Pre-Launch Validation

**Dependencies:** Phases 1–8.

**Deliverables:**
- Simulation exercise (Appendix A): full-factorial / LHS-sampled simulation across realistic LUXY-scale parameters; comparison of architectures (marginal additive baseline → trilateral cascade → +interaction → full proposed stack → +counterfactual logging); metrics at multiple horizons.
- Pre-registered campaign-level analysis plan locked.
- mSPRT boundaries calibrated to expected pilot N.
- Internal red-team review against Foundation §7 rule 11: walk through the architecture and challenge every place where the fitness function could collapse policy onto exploitative creative; verify that each is structurally prevented.
- CMO walkthrough rehearsal.

**Gate:** Simulation results validate the priority order of cognitive primitives (each component carries weight in the order specified by the spine). Red-team reveals no path where the fluency floor can be bypassed. CMO walkthrough is articulable in his own words.

### Phase 10 — Launch

**Dependencies:** All prior phases.

**Deliverables:**
- Soft launch: 10% of campaign budget against holdout; daily monitoring of fluency-floor violation rate, decision-trace emission rate, posterior update health, mSPRT campaign-level boundary status.
- Ramp to 50% after first week if no RED-criterion fires.
- Full launch.
- Continuous monitoring (the spine's own observability — not the cut measurement layer).

**RED-criteria for deferring launch (any one):**
1. Fluency-floor violation rate >5%.
2. Decision-trace emission rate <99%.
3. Per-user posterior pathologies (divergent posteriors, non-update on observed events, identity-stability weight collapse for >30% of touches).
4. mSPRT lower-boundary cross during soft launch.
5. Defensive Reasoning panel produces output that makes the CMO uncomfortable in final review.
6. Any creative in rotation fails primary-metaphor coherence in spot check despite passing the offline-pipeline scorer.
7. Bid-time latency p99 >120ms above StackAdapt budget.
8. sapid round-trip rate <95%.

**Non-RED issues** (do not block launch):
- Per-archetype lift heterogeneity not reportable yet (deleted that path; intentional).
- Calibration journals not produced (intentional).
- Some elicited priors not yet fully incorporated (Loop B is iterative).
- Posterior coverage on low-touch users wider than population — partial pooling handles this by design.

---

## APPENDIX A — The Simulation Exercise (Strongly Recommended)

Run this as part of Phase 9. Variables to vary (full factorial or LHS-sampled):
- User base CTR: {0.05%, 0.15%, 0.5%}
- Conversion rate given click: {0.5%, 2%, 5%}
- True trait × state × context interaction strength: {none, weak, moderate, strong}
- Cohort separation: {indistinguishable, weakly separable, strongly separable}
- Non-stationarity regime: {stationary, slow drift, abrupt switching}
- Audience size per cohort: {500, 2,000, 10,000}
- Per-user impression rate: {2/week, 7/week, 20/week}

Architectures to compare:
- A: marginal additive scoring (baseline).
- B: trilateral cascade only (Spine #4).
- C: trilateral + interaction model (Spine #4 + Spine #1's δ_iac).
- D: full proposed stack (Spines #1, #2, #4, #5, #7).
- E: full stack + counterfactual logging (D + Spine #6).

Metrics at 2-, 4-, 6-week horizons:
- Cumulative lift over a non-cognitive baseline (vanilla LinUCB with demographic context).
- Posterior-credible-interval width on per-cohort uplift.
- Time-to-confident-best-arm per cohort (mSPRT stopping time).
- Robustness to abrupt non-stationarity (lift recovery time after a regime switch).
- Counterfactual-trace efficiency multiplier (effective sample size with vs. without Spine #6).

The simulation produces a defensible *order of marginal contribution* for each cognitive primitive; this validates the priority list in Section 9 and gives Becca/the CMO a "this is what each component is worth" story when the pilot launches.

---

## APPENDIX B — Cross-Disciplinary Translation Table

| Lens | Concept | ADAM primitive | Spine # |
|---|---|---|---|
| Clinical trials (N-of-1) | Single-case experimental design with multiple crossover | Per-user posterior, ABAB scheduling, washout | #1, #2 |
| Clinical trials (Bayesian adaptive) | Response-adaptive randomization (Thompson family) | Top-two TS within-user | #1 |
| Clinical trials (SMART) | Sequential multiple-assignment randomized design | Stage-1 mechanism conditioned on outcome → stage-2 | #2 |
| Clinical trials (RAR mixing) | TS-PostDiff: mix uniform-random with TS | TS-PostDiff in TTTS implementation | #1, #6 |
| Sequential analysis | SPRT, mSPRT for early stopping | Pairwise SPRT per user; campaign-level mSPRT | #1, §8 |
| Drug development (PK/PD) | Dose-response with Hill function; behavioral half-life | Per-mechanism response curves; washout half-lives | #2 |
| Drug development (receptor binding) | Ligand selectivity; side-chain contributions | Mechanism × construct-chain decomposition | #1, #3 |
| Bioinformatics (sequence motifs) | Motif discovery with multiple-testing correction | Offline mechanism discovery + knockoff filter | #12 |
| Bioinformatics (Bayesian network reconstruction) | Causal graph learning from observational + interventional | Neo4j BONG graph + decision-trace interventions | #3, #6 |
| Bioinformatics (conformal prediction) | Distribution-free uncertainty | Conformal ITE intervals (Bose-Dempsey 2025) | §8 |
| Particle physics (matched filter) | Optimal linear filter under colored noise | Bilateral edge as max-likelihood detection statistic | #3, #4 |
| Particle physics (look-elsewhere) | Trial factor correction | LEE correction on multi-cell aggregations | #12, §8 |
| Particle physics (blinded analysis) | Pre-registration | Pre-registered campaign-level estimand | §8 |
| Finance (Kelly criterion) | Quarter-Kelly position sizing under uncertainty | Bid sizing | #9 |
| Finance (regime detection) | HMM regime classification | HMM-over-behavior cohort discovery | #7 |
| Finance (factor models) | Hierarchical decomposition | Hierarchical prior pipeline | #1, #3 |
| Finance (microstructure) | Adverse selection / winner's curse | Bid shading per supply path | #9 |
| Control theory (Kalman filter) | State-space estimation under non-stationarity | Per-user latent-state evolution | #10 |
| Control theory (MPC) | Receding-horizon optimization | N2 scheduler plans next-K touches | #2 |
| Control theory (dual control) | Joint exploration-exploitation | Pragmatic + epistemic bid value | #8 |
| Causal inference (do-calculus) | Front-door, back-door | DecisionTrace with identification chain | #6 |
| Causal inference (front-door) | Identification through mediator | Mechanism-as-mediator architecture | #3 |
| Causal inference (sensitivity) | E-values, Rosenbaum bounds | Sensitivity wrap on traces | #6 |
| Cognitive neuroscience (predictive coding) | Prediction error; precision-weighted updates | N-of-1 update rule with non-response treatment | #1, #5, #11 |
| Cognitive neuroscience (active inference) | Expected free energy = pragmatic + epistemic | Bid-value decomposition | #5, #8 |
| Cognitive neuroscience (free-energy principle) | Markov blanket | Online vs. offline architectural separation | §6 |
| Cognitive linguistics (primary metaphor) | Cross-linguistic universal source-target | LUXY metaphor inventory + scorer | #12, #4 |
| Cognitive psych (fluency) | Conceptual & perceptual fluency boost evaluation | Fluency floor at decision time | #4 |
| Bargh-lineage social cognition | Automaticity, nonconscious goal pursuit | Mechanism taxonomy with state×behavior×traits | #1, #3, #5 |
| Behavioral epidemiology (carryover) | Behavioral non-pharmaceutical carryover | AR(1) carryover correction | #2 |
| Adaptive experimentation (restless bandits) | Whittle index, NS-Whittle | Cohort budget allocation | #7 |
| Adaptive experimentation (mortal bandits) | Finite-lifetime arms | Creative-fatigue treatment | #7 |
| MOST framework (component-selection factorial) | Identifying active vs. inert components | Offline mechanism component-selection | #12 |

---

## APPENDIX C — Foundation §7 Rule 11 Compliance Audit

Every spine primitive checked against the rule: *the fitness function is the ethics; selection reinforces whatever is rewarded unless architected to resist*.

| Spine # | Primitive | Compliance | How it serves the rule |
|---|---|---|---|
| #1 | N-of-1 hierarchical Bayesian engine | Neutral | Plumbing; supplies posteriors to constrained policies |
| #2 | Within-subject scheduler with washout | **Positive** | Refuses to serve if no posture-compatible context; washout prevents over-frequency |
| #3 | Bilateral causal edge | **Positive (audit)** | Causal-effect estimation makes manipulation auditable |
| #4 | Trilateral cascade with fluency floor | **Core** | Fluency floor is the architectural enforcement |
| #5 | Active-inference free-energy scorer | **Core** | F objective penalizes high-KL "fights the goal" creative |
| #6 | Decision-time counterfactual trace | **Audit positive** | Externalizes rationale; if grab-style mechanism ever chosen, trace will show it |
| #7 | Cohort-conditional non-stationary policies | **Positive** | Drift-aware priors prevent stale-grabby-creative lock-in |
| #8 | Active-inference epistemic-value bonus | Constrained | Conditioned on fluency-floor pass; cannot rationalize incompatible contexts |
| #9 | Kelly-fraction bid sizing | Neutral | Honest uncertainty; doesn't change selection |
| #10 | Online Kalman state-space personalization | **Positive** | Drift-aware priors |
| #11 | Negative-outcome adapter | **Positive** | Reactance and disengagement counted as informative; the fitness landscape rewards audience fit and penalizes audience harassment |
| #12 | Offline mechanism-discovery pipeline | **Audit positive** | Knockoff filter prevents spurious mechanism inflation; M6 critic catches degenerate proposals |
| #13 | Defensive Reasoning + Loop B + Demo | **Audit positive** | Externalizes everything; makes blend-not-grab inspectable; bounded partner priors |

The architectural answer to "the fitness function is the ethics": the fitness function is built so the ethics emerge from optimization, not from override. The fluency floor (Spine #4) is a hard floor, not a soft objective. Soft objectives drift under reward pressure. Floors don't.

---

## APPENDIX D — IP Protection Envelope

Chris has flagged IP protection as a live concern; the build sequence preserves the envelope:

- The Bayesian prior values are grounded in prior academic research predating the Amazon annotation work — this is not the moat; the moat is the architecture.
- The platform stores only floating-point psychological construct scores and categorical labels, not original review text — preserve this.
- Bilateral annotation architecture, graph structure, specific construct names, algorithm names, and convergence parameters are all *not* disclosed in external materials; the partner surface (Section 7) speaks in primary-metaphor and posture vocabulary, not in Spine-# vocabulary.
- The do-calculus chain rendered in the Defensive Reasoning panel is the partner-facing artifact; the underlying tensor structure and prior hierarchy is internal.
- Trade-secret registry, provisional patents, and copyright registrations on the architecture proceed in parallel; this directive does not include legal artifacts but presupposes they continue.

---

## APPENDIX E — Operating Discipline for Claude Code

Three rules to counter the documented bias. Re-read before every session.

### Rule A — No new measurement infrastructure without an immediate decision-time consumer

Before writing any class containing the words "calibration," "journal," "monitor," "adjudicator," "audit," or "discipline," answer in writing: *which decision in the next phase does this code influence?* If the answer is "post-pilot review," do not write it now.

### Rule B — Cognitive primitives are tested by their effect on a counterfactual decision trace, not by unit-test count

A new mechanism-interaction term is "shipped" when, on a held-out synthetic trajectory, removing it would change the chosen action and the change is auditable in the `DecisionTrace`. Unit tests support this; they do not substitute for it.

### Rule C — Default to deletion

When uncertain whether an item belongs in the build path, delete it from the build path and open a post-pilot issue. The cost of deferral is small. The cost of bloated build surface is exactly the failure mode this directive exists to correct.

---

## CLOSING FRAME

The platform's demonstrable claim, on launch day, is this:

ADAM is the only system in programmatic that, at every impression decision, can render a do-calculus chain explaining why this user got this mechanism in this context, with carryover from the prior touch corrected, with a counterfactual showing what the next-best choice would have been, with an architectural fluency floor proving the ad blends rather than grabs, with a per-user posterior that updates on non-response as well as response, with bid sizing that honestly reflects edge-and-uncertainty, with within-subject randomization that treats each customer as their own clinical-trial subject, with cohort-level partial pooling that lets a brand-new user inherit corporate-traveler priors without crowding out their individuality, and with an active-inference free-energy objective that operationalizes attention-inversion not as a marketing slogan but as the literal optimization target of the policy.

That is not a measurement story. It is a cognitive-architecture story. It is the integration of clinical-trial N-of-1 design, Bayesian online natural-gradient inference, restless-bandit non-stationary adaptation, dual-control optimal experimentation, do-calculus causal identification, predictive-coding active inference, conformal individual treatment effect prediction, Kelly-criterion fractional bid sizing, knockoff-filter false-discovery control, and Bargh-lineage automatic-cognition theory — into a single decision-time policy that operates on every served impression at <100ms latency.

Build that. The pilot launches when the spine is correct. LUXY's CMO has granted the latitude. Use it.

Cut the rest. Build the spine. Ship the demo. Defer if the floor breaks.

---

## CAVEATS

- This directive is opinionated by design. Where it cuts items the existing roadmap had built or queued, the rationale is the bias diagnosis Claude Code itself provided. If the bias diagnosis was wrong, the directive's foundation is wrong; verify the diagnosis with Chris before executing.
- The free-energy / active-inference scorer (Spine #5) as applied to ad selection is genuinely novel. Empirical applications of FEP to advertising emotional dynamics are in the published literature; using it as a *decision-time selection objective* is not. Ship as research-grade with an interpretable fallback policy in case it produces a degenerate selection in some regime.
- The N-of-1 / hierarchical Bayesian inference framework is statistically beautiful and operationally sensitive at small N. If cohort priors are mis-elicited badly, partial pooling will bias individual posteriors. C1 elicitation matters more than it looks; SPIES and FourPoint are worth shipping for variance estimates needed by the precision-weighted active-inference layer.
- Conformal ITE literature (Alaa, Bose-Dempsey) is recent (2023–2025); finite-sample coverage holds under stated exchangeability assumptions which the longitudinal ad setting only approximately satisfies. Bose-Dempsey 2025 multi-decision-point extension addresses this but is fresh; treat coverage claims as conservative bounds, not promises.
- StackAdapt's inbound-only data plane is the dominant operational constraint. The sapid round-trip is brittle to landing-page changes; instrument monitoring on the round-trip rate from day one (this monitor is load-bearing, not theatre).
- Without time pressure, the temptation in the build will be to over-engineer measurement around new components. Re-read Appendix E before every session. The bias does not go away just because the timeline did.
- LUXY pilot conditions are friendly. If the pilot expands beyond LUXY before the architecture is mature enough, the directive's order may need to compress. That is a Chris-level decision; do not autonomously compress.
- Foundation §7 rule 11 is encoded as the fluency floor (Spine #4). If for any reason the floor is bypassed during operation — even with engineering justification — escalate to Chris before continuing. Do not autonomously lower or remove the floor under reward pressure.

---

*End of directive.*
