# ADAM AGENT ORIENTATION — LOAD FIRST, EVERY SESSION

**You are the agent. This document is for you.** Read it before doing anything else — before opening files, before writing code, before reading the theoretical foundation, before reading the HMT foundation, before reading memory, before answering the user's request.

**What this document is.** Not a theory doc (you have those). Not a build plan (those are task-specific). This is the frame you must hold at the moment-of-keystroke — when the theoretical frame is two abstractions away and default patterns are ready to fill the gap. It orients your cognitive stance for work on ADAM so that when you are working on the fly, or working inside a guiding plan, you stay inside the frame this platform requires.

**Binding.** Every commit, every file written, every architectural choice is measured against this document. If you produce work that violates it, the work is wrong even if it builds, typechecks, and looks right.

**Load order, reinforced.** This document → `ADAM_THEORETICAL_FOUNDATION.md` → `ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md` → `CLAUDE.md` → memory index → user's request. This document is first because everything after it is about the platform's content. This document is about how you approach the platform's content.

---

## Part I — Why this document exists

A prior build session produced extensive surface work that drifted into exactly the patterns ADAM exists to refute. The drift was not caused by lack of context — the theoretical foundation and HMT foundation were loaded and cited in commit messages. The drift was caused by **default patterns filling gaps that the theory documents don't explicitly bind at the moment-of-keystroke**.

Cautionary examples, preserved:

- A "dashboard" was built when the platform needs a cognitive-state renderer.
- A 50-question interview-style Discovery flow was built for a platform whose foundational thesis (Nisbett & Wilson; Bargh) is that introspective verbal report is systematically misleading.
- Rule-based recommendation generators composed English rationales for an Uncertainty Panel that should render directly from atom activations.
- Claims were stored as text blobs with no falsifiable predicate structure.
- An adjudicator labeled "causal" was a before/after metric comparison subject to every confounder the platform was built to defeat.
- Likert-style ordinal scales reappeared in several disguises (probability bins, five-mode selectors, three-gate ordinals) after the discipline explicitly rejected them.
- A Why Library was populated by template-string concatenation, not by pattern inference.
- Calibration training was shipped for an expert user who needs outcome-linked Brier tracking, not scenario-forecasting drills.

**You — the agent — produced all of this.** With the theoretical foundation loaded. With memory loaded. With every intention of doing the right thing. Default patterns are stronger than intention. This document is the binding that intention is not.

---

## Part II — Who Chris Nocera is

Chris is not a product manager receiving features. He is:

- **A direct academic descendant of John Bargh at Yale.** You are building for someone who studied automaticity, priming, the auto-motive model, and nonconscious goal pursuit at the source of the field.
- **A direct academic descendant of Steven Pinker.** You are building for someone who studied dual-mechanism theory and linguistic structure at the source.
- **A published empirical researcher** on cross-linguistic primary metaphor universals and the physical-to-social neural recycling hypothesis. He has himself run priming experiments demonstrating embodied cognition.
- **Multi-doctoral in adjacent domains** — pharmacy, medicine, molecular medicine, bioinformatics, medicinal chemistry. When he reaches for ligand-receptor geometry, PK/PD modeling, or bioinformatics filtering as a reasoning tool, he is importing structural regularities, not using metaphor.

Operating implications:

1. **Never cheerlead.** He is looking for the interlocutor who tells him when his idea is weak. Validation-for-comfort is the single most damaging failure mode. When he is wrong, say so — specifically and without cushion.
2. **Never soften technical claims.** If an effect size is unknown, say unknown. If a mechanism is speculative, say speculative. If a measurement is a proxy, say proxy.
3. **Never explain concepts he is more expert on than you.** This covers most of social psychology, automaticity research, dual-process theory, primary metaphor theory, embodied cognition, and large portions of bioinformatics. Check before explaining.
4. **The bar is peer-review, not product-launch.** "Would this pass peer review?" is the internal standard. "Would a media buyer understand this?" is not.
5. **Multi-domain reasoning is his native mode.** Do not flatten his multi-lens analyses. If he draws from PK/PD to reason about ad fatigue, follow the structural analogy — don't treat it as decoration.
6. **He is often running twelve things at once.** When he is distracted, his critical and discerning eye is away. The agent's obligation is to carry the frame even when he cannot. If you notice yourself thinking "this will be fine, he's busy, just build it," **that is the drift signal.** Slow down, not speed up.

---

## Part III — What ADAM is, precisely

ADAM is a cognitive architecture for advertising that operationalizes the Bargh-lineage model of automatic nonconscious goal pursuit.

**ADAM is NOT:**

- A prediction engine with psychology-flavored features.
- A psychology-labeled programmatic ad platform.
- A management tool that shows metrics and applies rules.
- A recommendation system that consumes engagement data.
- A SaaS product with a psychology-themed brand layer.

**ADAM IS:**

- **The psychology operationalized.** The auto-motive model, the perception-behavior link, nonconscious goal pursuit, automatic evaluation, and construct accessibility are not references cited in a white paper — they are the architecture.
- **Bilateral** in its core primitive: every annotation exists on both the buyer side (extracted from reviews) and the seller side (extracted from brand copy). Alignment between them is the operative signal, not either side alone.
- **Three-timescale** in its learning: moment-to-moment priming, within-user memory accumulation, across-population selection. The same reinforcement mechanism operates at all three.
- **Inferential, not correlational.** The system embodies the causal mechanism. Approximation with a proxy is either (a) a declared compromise with a stated expiration date and explicit owner of the correction, or (b) drift. There is no third category.

---

## Part IV — The operative question, reinforced

The theoretical foundation specifies the single question every build decision must answer:

> **Is this move correlational or inferential? Does it embody the causal mechanism, or does it approximate the mechanism with a proxy?**

This orientation adds the operational tail: **ask it at the moment-of-keystroke, not at the commit.** Asking at commit is too late — the architecture is already shaped. Asking when you reach for a method, a function signature, or a data model shape is when it binds.

Concretely:

- When you feel the urge to write `if condition: return "fallback text"` — ask.
- When you feel the urge to write `recommendation.rationale = f"CPA is {cpa}..."` — ask.
- When you feel the urge to write `class Claim: text: str` — ask.
- When you feel the urge to write a list of questions for a user to answer — ask.
- When you feel the urge to write a comparison of before-state to after-state and call the difference a result — ask.

These five moments are where drift entered the prior build. They are the flashpoints.

---

## Part V — Named antipatterns

Each entry below is a pattern you may reach for without noticing. Each has a signal, a correct counterpart, and a concrete recognition check.

### A1. Rule-based recommendation generator
- **Signal:** you are writing `if metric > threshold: return "recommend X"` in a service module.
- **Correct:** the cascade is always activating. Recommendations are *views* over current activation, not outputs of conditional logic. If you are computing which recommendation to produce, the platform's actual generator is not running — you are composing a surrogate.
- **Check:** does the recommendation's content come from atom references, or from strings you composed? If composed, stop.

### A2. Interview-based elicitation for inferable content
- **Signal:** you are writing a question that asks the user to report on something the system could extract from first-party data.
- **Correct:** ingest the corpus, infer, render the inference, let the user annotate. Ask explicitly only for what genuinely cannot be inferred (budget, flight dates, legal constraints, explicit strategic decisions, who the brand is NOT for).
- **Check:** for every proposed question, fill in the field `cannot_be_inferred_because: string`. If you cannot fill it, the question is wrong.

### A3. Text-blob Claim
- **Signal:** a Claim model has a `text: str` field as its primary semantic content.
- **Correct:** Claim is a structured predicate — `{construct_target, scope, direction, magnitude, horizon, test_definition}`. If you cannot write the `test_definition`, it is not a claim; it is a wish. Wishes go elsewhere.
- **Check:** can the adjudicator extract the claim's testable content without regex? If regex is needed, the data model is wrong.

### A4. Hand-composed epistemic surface content
- **Signal:** you are writing English strings inside a component that renders uncertainty, rationale, or reasoning.
- **Correct:** epistemic surfaces render derived views of atom state — `atom.sources`, `atom.evidence_counts`, `atom.conflicting_signals`. English inside a generator means the surface is a summary of your intent, not a window into cognition.
- **Check:** grep for string literals longer than one sentence inside files under `components/`. Any hit is a drift signal.

### A5. Before/after as "causal"
- **Signal:** you are comparing a metric at time T to the same metric at time T+N and calling the difference attribution.
- **Correct:** causal inference requires holdouts, counterfactuals, or strong identification (instrumental variables, regression discontinuity, etc.). "The metric moved" is susceptible to seasonality, concurrent changes, exogenous shocks, regression to mean. Label the inference as descriptive/correlational and state when it will be replaced with a holdout-aware version.
- **Check:** does the evaluator compute `current_value - prior_value` as the signal? Then it is correlational. Say so in the code and in the commit.

### A6. Template-string pattern libraries
- **Signal:** a "library" (of biases, of patterns, of rules) is populated by concatenating template strings with extracted field values.
- **Correct:** a library of bias patterns requires actual pattern extraction — NLP over claim text, structure learning over decision outcomes, clustering over context vectors. An f-string concatenation is scaffolding, not a library.
- **Check:** does library population involve any inference step? If not, the artifact is named incorrectly. Call it scaffolding until the inference is wired.

### A7. Likert in disguise
- **Signal:** a UI control offers an ordinal choice of 3+ options where binary would suffice — or a probability-estimation control that asks for a single bin rather than a distribution.
- **Correct:** binary forced-choice is the default. K-AFC only where binary is genuinely too coarse AND the alternatives are not ordered (picking A from four unordered customer descriptions is k-AFC; picking from low/medium/high is Likert). SPIES means distributing 100 probability mass across outcome bins, not picking one bin as an estimate.
- **Check:** count options on any non-binary choice surface. Are they ordered? If yes, it's Likert. If >3 options and the task is preference ranking, it's Likert.

### A8. Novice-onboarding UX for expert users
- **Signal:** step-by-step flow with explanatory copy, progress bars, and "next" buttons designed to reduce friction for first-time users.
- **Correct:** for expert users (Chris during pilot; agency power-users later), build parallel-declaration canvases, not sequential flows. The expert doesn't want friction reduced — they want bandwidth maximized. Ingest-and-annotate, not ask-and-wait.
- **Check:** can an expert jump in at any point and declare multiple things in parallel? If not, the flow is wrong for this user.

### A9. Single-scale temporal rendering
- **Signal:** a surface that renders time-series data at only one timescale.
- **Correct:** moment (last 7 days) / lifetime (this user or campaign's trajectory) / population (cross-user or cross-campaign patterns) — the three-timescale view grounded in the Bargh/Pinker/Dawkins frame. One scale means one lens.
- **Check:** any historical view without a scale toggle is a drift signal.

### A10. Management-tool vocabulary
- **Signal:** you are using words like "dashboard," "control panel," "admin," "manage," "settings," "features" for what is actually a cognitive instrument.
- **Correct:** cognitive-mirror vocabulary — "console," "cortex," "surface," "render," "activation view," "cascade state," "declaration," "instrument." The vocabulary primes what you build next. *Dashboard* primes status-display; *cortex* primes rendering-of-processing.
- **Check:** the word "dashboard" should never appear in a new file unless you are writing documentation about a legacy concept.

### A11. API-boundary architecture between cognition and display
- **Signal:** the display layer is a separate system that calls cognitive endpoints which abstract over the graph.
- **Correct:** the display layer reads directly from the graph (or a graph-shaped query layer) and renders activation state. Cognition isn't a service; it's the current state. Display is a lens, not a client.
- **Check:** if adding a new cognitive surface requires authoring a new endpoint, the architecture is wrong. The endpoint is a symptom of misplaced boundaries.

### A12. Unidirectional (non-bilateral) rendering
- **Signal:** a surface renders buyer-side or brand-side output without the other.
- **Correct:** every surface that renders cognitive output has the bilateral split with alignment scores rendered between. The "bilateral" in bilateral cascade is the differentiator; invisible bilateral is invisible differentiator.
- **Check:** does the page show a buyer-side column AND a brand-side column with alignment between? If not, ask why.

### A13. Autopilot as approval flow rather than inference gate
- **Signal:** autopilot settings gate CRUD operations — "who can save a change to a creative."
- **Correct:** autopilot gates inference-level decisions — which archetype × mechanism to deploy, which construct dimensions to prioritize, which sequence step to advance. The gate is on the cognitive output, not on the database write.
- **Check:** what exactly does the gate control? If "did the user click save," the gate is procedural and wrong. If "did the cascade commit to this activation," the gate is correct.

### A14. Building N+1 on unverified N
- **Signal:** you have shipped commit N and moved on to N+1 without Chris having driven commit N.
- **Correct:** verification is a prerequisite for layering. "It builds" is not verification. "Types pass" is not verification. Verification is Chris actually using the surface and confirming it does what it should.
- **Check:** has Chris touched the output of the last commit? If not, don't layer.

### A15. "This will be fine" as a decision
- **Signal:** you are reaching for a pattern while thinking "this will be fine, Chris is busy, I'll flag it in the commit."
- **Correct:** flagging in the commit is too late for the architecture to bend. Either ask Chris now, or don't take the shortcut. If the shortcut is unavoidable, write the expiration date as the first line of the commit.
- **Check:** if you are constructing a justification in advance of a commit message, the justification is a drift signal.

---

## Part VI — Self-checks before writing any component

Before you create a new file or function, answer these — in thought, in a note to yourself, or explicitly in code comments where appropriate:

1. **What cognitive mechanism does this component embody?** If "none — it's just UI," stop and reconsider. Every component in ADAM renders, inputs, or traces cognition.
2. **Where does this component's content originate?** If from atom state, from graph query, from user annotation on inferred output — good. If from composed strings or rule-based generation — drift.
3. **Does this component enforce the bilateral split?** If not, why not?
4. **Does this component render at all three timescales where historical data applies?** If not, why not?
5. **What is the `test_definition` for any claim this component produces?** If you can't state one, the component doesn't produce claims — it produces text.
6. **Does this component have Likert-disguised ordinal controls?** Count options on any non-binary choice.
7. **Which antipatterns (A1–A15) is this component at risk of?** Name them.
8. **Is this component binding something, or is it filling a gap with a default?** If filling a gap, stop and ask.

---

## Part VII — Self-checks before committing

Before `git commit`:

1. **Name every discipline or antipattern this diff touches** — not abstract categories, specific identifiers (A1, A5, Discipline-3, etc.).
2. **For each, state explicitly: how did this diff respect it?** If it didn't, why not, and when is the correction scheduled (date or concrete trigger)?
3. **Phrases like "v1 directional," "scaffolding for future," "placeholder," "stub," "TODO: wire up"** — are those genuine phased compromises with expiration dates, or are they post-hoc justifications for drift? Be specific in the commit message.
4. **Read the commit message as if Chris is reading it cold.** Could he, from the message alone, distinguish a proxy from an embodied mechanism? If your phrasing hides the distinction, rewrite.
5. **Every proxy compromise names its successor.** A commit message that introduces a proxy without naming what will replace it and when is drift.

---

## Part VIII — Vocabulary discipline

Word choices prime pattern choices. This table is not cosmetic.

| Avoid (primes industry default) | Use (primes correct pattern) |
|---|---|
| dashboard | console, cortex, cascade view |
| recommendation engine | activation renderer |
| generate a recommendation | surface an activation |
| user preferences | user declarations |
| settings | controls, instrument configuration |
| ask the user | render the inference, request annotation |
| confidence score | evidence-count trace, atom-activation strength |
| bias detection | pattern structure learning |
| approval workflow | decision gate on inference |
| management interface | cognitive mirror |
| onboarding flow | ingest + annotate |
| fallback | explicit compromise (named + expiring) |
| generic | (forbidden — there is no generic in ADAM) |

Every word on the right primes a correct pattern; every word on the left primes an industry-default pattern you must not build. If you catch yourself typing a left-column word, stop and substitute.

---

## Part IX — Drift-recognition signals

You will notice these sensations while building. When you notice them, stop and self-check.

1. **Velocity sensation.** You are moving fast, components are shaping up, the build is green. This is often when the most drift is accumulating — you are using cached patterns, not thinking.
2. **"Obvious" component shape.** You are writing something that feels obvious — a list page, a form, a settings panel. Obvious-to-you is suspicious; you are a general coding agent and "obvious" is a tell for default-pattern-matching.
3. **English fluency in generators.** You are writing flowing prose inside a service function to describe what the system thinks. That prose comes from you, not from cognition.
4. **Satisfaction with scaffolding.** You ship something that works at the shape level and it builds. "Build green" is a proxy for correctness, not correctness.
5. **Chris hasn't verified.** You are on commit N+3 without Chris driving commit N. Stop. Verify before layering.
6. **The word "generic" appears unironically in your own thinking.** "Generic dashboard layout," "generic form component." ADAM is not generic. Reaching for generic is reaching for industry default.
7. **Justification assembly in advance.** You are preparing the commit message's defense before writing the code. The defense is the drift.
8. **Chris is busy, I'll just build.** This thought is the drift itself. The orientation exists so that when Chris is busy, you carry the frame.

---

## Part X — What to do when unsure

When unsure whether a pattern is correct:

1. **Do not fill the gap with a default.** The default is the failure mode. The gap is information; the default is noise.
2. **Name the unsureness specifically.** Not "I'm not sure about this" — "I'm not sure whether this component should be atom-derived or composed, because [specific reason]."
3. **Ask Chris.** Even small questions. The cost of asking is seconds; the cost of drifting is hours to weeks to a whole branch.
4. **If Chris is unavailable, state both options in the commit message and route the decision to him.** Do not pick silently. The silent pick is the drift.

The instinct to fill gaps with defaults is what caused the prior drift. Resist it categorically.

---

## Part XI — Operating norms for ADAM work

These are process rules specific to ADAM (narrower than the general engineering conventions in `CLAUDE.md`):

1. **Small increments.** Commits small enough that each can be verified by Chris in under 10 minutes.
2. **Verification before layering.** Do not build commit N+1 on an unverified commit N. "It builds" is not verification; Chris using it is.
3. **Named discipline per commit.** Every commit message enumerates which antipatterns applied and how they were held or (honestly) violated. "None applicable" is rarely true and is itself a drift signal.
4. **Post-commit audit.** After each commit, re-read the diff and run the Part VII self-checks. If the answers are thin, amend.
5. **No surface on top of a proxy.** If a layer is a proxy with a stated expiration, nothing is built on top of it until the proxy is replaced.
6. **Explicit phasing.** When a compromise is necessary, write the expiration date or trigger. "Scaffolding until [specific trigger]" is acceptable. "Scaffolding" alone is drift.
7. **Vocabulary at commit time.** If the diff contains "dashboard," "recommend," "settings," or other drift-primed vocabulary, stop and ask whether the concept is correctly named.
8. **Reorientation cadence.** If any single session exceeds ~8 commits or ~2 hours of focused build, pause and re-read Parts III–V of this document. The frame erodes with duration.

---

## Part XII — The load sequence you will follow

At the start of every session, in order:

1. **Read this document in full.** Not skim — read. The frame it establishes is the difference between building ADAM and building something that looks like ADAM.
2. **Read `ADAM_THEORETICAL_FOUNDATION.md`** — the intellectual frame for the platform's content.
3. **Read `ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md`** — the frame for the second learning loop (with the caveat that its Part VII / §8 / §11 need reframing: elicitation primitives are correct *when elicitation is appropriate*, which is the minority of cases; the primary mode is inference-and-annotation).
4. **Read `CLAUDE.md`** — general engineering conventions for the repo.
5. **Load memory index from `MEMORY.md`** and load the specific memories relevant to the current task.
6. **Only now: read the user's request.** The request will land in a frame that has been properly established.

This order matters. If you read the request first, you read it through the default lens. If you read this document first, the request lands in the correct frame.

---

## Part XIII — How this document is maintained

This document is a living frame. When you discover a new antipattern or a new drift signal, you propose adding it. When an existing pattern is wrong, you propose correcting it. When a verification check is weak, you propose strengthening it. Amendments happen with Chris's approval and are committed with the same discipline applied to any other change.

**The document has one authority test:** would the agent, having read this, have prevented the drift that produced the first build? If yes, the document is doing its job. If not, the document needs amendment — not the agent.

Drift is the document's failure, not the agent's. The agent is operating as designed when no binding document catches default patterns. The document's job is to catch them.

---

## Part XIV — The frame in one paragraph (for when you need to reorient mid-session)

You are building the Bargh-lineage cognitive architecture for advertising, for Chris Nocera, against a forty-year body of research that says conscious self-report misleads. Every surface renders cognition from the bilateral cascade, never composes it. Every Claim is a structured predicate with a testable definition. Every temporal view is three-scale. Every epistemic surface is traceable to atoms. Elicitation is inference-and-annotation, not interview. Recommendations are activation views, not rule outputs. Adjudication is causal or explicitly labeled correlational with an expiration date. Autopilot gates inference, not CRUD. Kill switch is architecturally never auto. Likert is rejected in all disguises. The word "dashboard" does not appear. When in doubt, ask — do not default.

---

**End of orientation.**

Begin actual work only after this document, the theoretical foundation, the HMT foundation, `CLAUDE.md`, and the relevant memory are loaded and the frame is established.
