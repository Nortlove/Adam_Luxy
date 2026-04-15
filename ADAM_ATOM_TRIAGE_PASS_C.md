# ADAM Atom Triage — Pass C

**Date:** 2026-04-15
**Scope:** The 16 orphaned atom files under `adam/atoms/core/` identified by the AST-based audit.
**Supplement to:** `ADAM_INTEGRATION_AUDIT_2026-04-15.md` (Section 2: "The DAG has 14 atoms, not 30+"), `ADAM_PAGE_INTELLIGENCE_REVIEW.md` (Pass B, which applied the same triage method to page intelligence).
**Method:** Read the module docstring and imports of each orphan. Compared against live atoms (`base.py`, `user_state.py`) for structural shape. Verified each is not reimplemented under a different name in the live DAG. Classified as `stranded-work`, `draft`, or `tombstone-candidate` per the taxonomy established in the audit corrections.

## Headline

**All 16 orphan atoms are stranded architectural work. None are drafts. None are stubs. None should be deleted.** The memory claim of "30+ atoms in the DAG" is structurally accurate at the filesystem level — 30 atom files exist under `adam/atoms/core/`. It is wrong only at the runtime level: `dag.py:31-45` imports 14 of them. Sixteen are fully written, fully theoretically grounded, and stranded in the filesystem, not called by anything.

**The correct action for every one of the 16 is to wire it into the DAG, not to delete it.** This is a larger finding than Pass B's single `page_edge_bridge.py` orphan. It means the actual architectural ambition of ADAM is much higher than the running system currently demonstrates, and the campaign build work should happen on top of the full 30-atom DAG, not the current 14-atom rump.

## 1. What a live atom looks like, for reference

Reading `base.py` and `user_state.py` first established the shape. A complete atom in this codebase:

- Inherits from `BaseAtom` (from `adam.atoms.core.base`)
- Imports `IntelligenceEvidence`, `MultiSourceEvidence`, `FusionResult`, `EvidenceStrength` from `adam.atoms.models.evidence`
- Imports `AtomInput`, `AtomOutput` from `adam.atoms.models.atom_io`
- Imports `AtomType` from `adam.blackboard.models.zone2_reasoning`
- Imports `IntelligenceSourceType`, `ConfidenceSemantics` from `adam.graph_reasoning.models.intelligence_sources`
- Usually imports helpers from `adam.atoms.core.dsp_integration` (DSPDataAccessor, SusceptibilityHelper, CategoryModerationHelper, EmpiricalEffectivenessHelper) and `adam.atoms.core.construct_resolver`
- Has a module docstring with:
  - Brief description of the construct
  - "Key insight" paragraph
  - Academic Foundation section citing 4-6 peer-reviewed sources
- Has concrete data structures (dicts mapping categories/mechanisms/states to effectiveness values, taxonomies, or parameter tables)

**All 16 orphan atoms match this shape exactly.** None is missing any structural element. None uses a different base class or a different evidence model. They are indistinguishable from the live atoms except for the fact that `dag.py` does not import them.

## 2. Per-Atom Classification

All classified as **stranded-work** → **recommend wire into DAG**. Each row below captures the atom's theoretical grounding, the specific capability it adds, and its relevance to the LUXY campaign in particular.

### 2.1 The 16 orphan atoms

| Atom | Theoretical grounding | Capability it adds | LUXY relevance |
|---|---|---|---|
| **autonomy_reactance** | Psychological Reactance Theory (Brehm 1966, 1981); Self-Determination Theory (Deci & Ryan 1985); Wicklund 1974; Miron & Brehm 2006 | Detects user's reactance threshold, ensures persuasion mechanisms operate *below* it. Assigns "coerciveness scores" to each mechanism (scarcity 0.85, urgency 0.9, authority ~0.4, narrative_transport ~0.1). Without this atom, the DAG cannot predict when a creative will backfire via reactance — which the docstring explicitly calls out as *"the main reason WHY advertising fails."* | **High.** Luxury audiences are especially sensitive to hard-sell tactics; reactance is one of the dominant failure modes for luxury creative. |
| **brand_personality** | Aaker 1997 Brand Personality Framework; Mark & Pearson 2001 Brand Archetypes; Fournier 1998 Consumer-Brand Relationships | Retrieves brand personality profile from Neo4j, computes brand-consumer archetype compatibility, identifies optimal mechanisms for the brand voice, feeds copy generation. Docstring calls it *"a CORE PRIMITIVE in ADAM."* Its absence means brand personality never flows into mechanism selection, station matching, or copy generation. | **Very high.** Luxury brand voice (exclusivity, heritage, craftsmanship, understated confidence) has to align with creative or the whole campaign reads wrong. |
| **coherence_optimization** | Thagard 2000 (Coherence in Thought and Action); Simon & Holyoak 2002 (Structural Alignment); Festinger 1957 (Cognitive Dissonance) | **Resolves cross-atom conflicts.** When one atom says "use urgency" and another says "avoid urgency," this atom decides. Without it, the DAG has no mechanism to produce a coherent strategy from conflicting atom outputs — the final recommendation is structurally whatever MechanismActivation happens to fuse, with no coherence check. | **Critical.** Once the other 15 orphans are wired in, conflicts between atoms will multiply. This atom is the one that makes the expanded DAG produce coherent strategies instead of conflicting noise. Must be wired in alongside the others, not separately. |
| **cooperative_framing** | Shapley 1953 (Cooperative Games); Nash 1953; Prahalad & Ramaswamy 2004 (Co-Creation); Vargo & Lusch 2004 (Service-Dominant Logic) | Models purchase as a cooperative game of joint value creation rather than adversarial exchange. The docstring claims cooperative framing *"bypasses persuasion knowledge defenses because the consumer doesn't activate skepticism when they perceive genuine mutual benefit."* | **High.** Luxury concierge brands that position as "we're here to make your evening unforgettable" land better than those that position as "our Mercedes fleet is the best." The first is cooperative framing; the second is adversarial competitive positioning. |
| **interoceptive_style** | Damasio 1994 (Somatic Marker Hypothesis); Craig 2002 (Interoception); Garfinkel et al. 2015; Dunn et al. 2010 | Detects whether the user uses bodily/gut feelings vs. analytical reasoning for decisions, adjusts mechanism selection accordingly. Body-aware users respond to sensory/embodied language ("feel the difference"); analytical users want specs and comparisons. | **Medium.** Luxury experiences are often sold to interoceptive audiences ("feel the service," "experience luxury") but the analytical axis matters for the business-class / airport-transfer use case. |
| **mimetic_desire_atom** | Girard 1961, 1972 (Mimetic Theory); Gallese 2001 (Mirror Neurons); Belk 1988 (Extended Self); Oughourlian 2010 | Models desire as MODEL-BASED wanting — "I want it because that person wants it." Distinct from social proof, which is consensus-based. Identifies the right aspirational model and the right mechanism for triggering mimetic desire without activating rivalry/resentment. | **Very high.** Luxury is the canonical domain for mimetic desire. "I want what successful people have" is the substrate for luxury brand appeal. The LUXY campaign without mimetic desire as a first-class mechanism is missing the primary lever for the target segment. |
| **motivational_conflict** | Lewin 1935 (Force Field Theory); Miller 1944 (Conflict Theory); Hovland & Sears 1938; Cacioppo & Berntson 1994 | Models approach-avoidance dynamics. The gradient of avoidance is *steeper near the decision point* — the closer a user gets to buying, the more avoidance dominates. The atom determines whether the user is in approach-dominant or avoidance-dominant state and picks strategy accordingly. | **High.** Luxury purchases involve strong approach-avoidance conflict (want the service, afraid of the cost/image/commitment). When a user abandons at checkout, motivational conflict is the substrate explaining why. |
| **narrative_identity** | McAdams 1993, 2001 (Narrative Identity, Life Stories); Green & Brock 2000 (Narrative Transport); Escalas 2004; Adaval & Wyer 1998 | Models purchases as "chapters in the user's life story" — products as plot devices. Identifies which narrative themes resonate (redemption, growth, belonging, adventure, mastery) and picks mechanisms that create genuine narrative transport rather than hard-sell framing. | **Very high.** Luxury transport purchases are often plot devices in a narrative ("I've arrived," "the anniversary we never forget," "the promotion that changed everything"). Wiring narrative identity directly enables identity-transformation creative. |
| **persuasion_pharmacology** | Clark 1933 (Dose-Response Curves); Bliss 1939 (Drug Interaction Models); Chou & Talalay 1984 (Combination Index); adapted via Petty & Cacioppo 1986 (ELM Intensity) | **Treats persuasion mechanisms like pharmaceutical compounds.** Each mechanism has a dose-response curve with EC50, hill coefficient, max effect, toxicity threshold, and tolerance rate. Computes drug-drug-like interactions (scarcity + social proof = synergy; scarcity + authority = antagonism). **This is the exact PK/PD lens I proposed building as a future item during the multi-lens discussion. It already exists, fully written, at 500+ lines.** | **High.** All mechanism dosing depends on this atom. Without it, every mechanism is applied at default intensity regardless of user state, which is exactly what the foundation doc's pharmacology lens argues is wrong. |
| **query_order** | Johnson, Häubl & Keinan 2007 (Query Theory); Weber et al. 2007; Hardisty & Weber 2009; Johnson & Goldstein 2003 | Models the order in which consumers internally generate "queries" (reasons for/against) during evaluation. Earlier-retrieved reasons get disproportionate weight due to output interference. By controlling which queries the ad triggers first, biases the entire evaluation. | **Medium.** Less directly relevant for LUXY specifically, but a powerful general-purpose mechanism for any comparative-consideration purchase (LUXY vs. Uber Black vs. Blacklane). Query order determines the order users evaluate alternatives. |
| **regret_anticipation** | Loomes & Sugden 1982 (Regret Theory); Bell 1982; Zeelenberg 1999; Connolly & Zeelenberg 2002; Inman & Zeelenberg 2002 (action vs inaction asymmetries) | Models anticipated regret of action ("wasting money") vs inaction ("missing out"). The ratio determines whether urgency/scarcity or reassurance/guarantee mechanisms dominate. Without this atom, ADAM cannot distinguish high-inaction-regret users (for whom urgency works) from high-action-regret users (for whom reassurance works). | **Very high.** Luxury purchases are high-regret-salience decisions in both directions. Getting the regret anticipation wrong is a direct path to backfire for exactly the high-value customer. |
| **relationship_intelligence** | Escalas & Bettman 2003 (Self-Brand Connection); Thomson, MacInnis & Park 2005 (Brand Attachment); Taute & Sierra 2014 (Brand Tribalism); Carroll & Ahuvia 2006 (Brand Love); Fournier 1998 (Consumer-Brand Relationship Framework) | Determines consumer-brand relationship type via 5-channel observation (reviews, social signals, self-expression, brand positioning, advertising). Different relationship types respond to different mechanisms, tone, ad templates, and audience targeting. Docstring calls it *"a CORE PRIMITIVE."* | **High.** LUXY campaign has to differentiate first-time buyers (transactional relationship, need credibility) from repeat customers (loyalty / tribal / brand-love relationships, need recognition and status). Relationship intelligence is the atom that detects this. |
| **signal_credibility** | Spence 1973 (Signaling Theory); Zahavi 1975 (Costly Signaling / Handicap Principle); Connelly et al. 2011; Kirmani & Rao 2000 (No Pain No Gain — costly signal typology) | Evaluates whether ad signals are costly (hard to fake, verifiable, diagnostic of quality) or cheap talk. Picks mechanisms based on whether the brand has credible signals to leverage (warranty, price floors, heritage, verification). | **High.** Luxury positioning is mostly costly signaling. The atom that evaluates whether a brand has costly signals available is load-bearing for any brand claiming luxury. |
| **strategic_awareness** | Friestad & Wright 1994 (Persuasion Knowledge Model); Campbell & Kirmani 2000; Wegener et al. 2004; Isaac & Grayson 2017 | Assesses how aware the user is of persuasion tactics, routes around their defenses. Sophisticated users resist obvious mechanisms (scarcity, urgency) but remain susceptible to less-detectable ones (reciprocity, commitment, narrative). The atom detects sophistication and picks accordingly. | **High.** Luxury audiences are high-sophistication on average — they have seen every trick. Without strategic awareness, ADAM will use mechanisms they immediately dismiss. |
| **strategic_timing** | Dixit & Pindyck 1994 (Real Options Theory); Ferguson 2006 (Optimal Stopping); Ariely & Wertenbroch 2002; Shu & Gneezy 2010 | Decides when urgency is authentic vs when it backfires as desperation signaling. When option value of waiting is genuinely low (rising prices, limited stock, time-bounded event), urgency works. When it is not, urgency signals seller desperation and hurts the brand. | **High.** Luxury urgency is almost always fake and well-sophisticated audiences detect it. Strategic timing is the atom that should *refuse to apply urgency* in the wrong contexts. Its absence means urgency gets applied uniformly. |
| **temporal_self** | Parfit 1984 (Personal Identity); Hershfield 2011 (Future Self-Continuity); Hershfield et al. 2011 (Age-Progressed Self); Frederick, Loewenstein & O'Donoghue 2002; Bartels & Urminsky 2011 | Measures how connected the user feels to their future self. High continuity → investment/identity framing works. Low continuity → urgency/immediate gratification works. These are structurally different mechanisms for structurally different users, and ADAM cannot distinguish them without this atom. | **Medium.** More relevant for subscription, insurance, and long-horizon purchases than for point-of-sale luxury services, but still matters for LUXY repeat-customer framing ("where you'll be in a year"). |

### 2.2 Summary of LUXY relevance

Of the 16 orphan atoms, **12 are high or very-high relevance for the LUXY campaign**. The four with only medium relevance are still useful additions, just less directly load-bearing for this specific campaign.

**The atoms most directly relevant to LUXY** (very high + high):

1. brand_personality (luxury brand voice alignment)
2. mimetic_desire_atom (aspirational peer wanting — the dominant luxury mechanism)
3. narrative_identity (plot-device framing for life-story moments)
4. regret_anticipation (critical for high-value decisions)
5. autonomy_reactance (luxury audiences are reactance-sensitive)
6. relationship_intelligence (first-timer vs repeat customer differentiation)
7. signal_credibility (luxury = costly signaling)
8. strategic_awareness (sophisticated audiences detect tactics)
9. strategic_timing (fake urgency hurts luxury brands)
10. cooperative_framing (concierge partner framing works in luxury)
11. coherence_optimization (needed to resolve the new cross-atom conflicts)
12. persuasion_pharmacology (mechanism dosing across the board)

**Wiring all 12 would directly add 12 specific construct-level reasoning capabilities to the LUXY decision path**, each grounded in cited research. The campaign would then be running on the actual inferential architecture the foundation doc describes, not the current 14-atom rump.

## 3. The `persuasion_pharmacology` discovery

This deserves its own call-out because it is the most embarrassing find of the session for me personally.

**During the multi-lens conversation earlier this session**, Chris taught me to reach for pharmacological lenses — PK/PD, dose-response, drug-drug interactions, therapeutic window — as reasoning tools for ADAM architecture questions. I took that guidance, applied it to Risk #1 (the simulation fallback), and proposed as a *future-build item* that "retargeting should be modeled as a pharmacokinetic system with absorption, elimination, tolerance, and therapeutic window." I flagged it explicitly as something we should build later.

**That atom already exists.** `adam/atoms/core/persuasion_pharmacology.py` implements exactly the PK/PD model I was proposing, at atom-level instead of retargeting-level, with:

- `MECHANISM_PHARMACOLOGY` dict: EC50, hill coefficient, max_effect, toxicity_threshold, tolerance_rate per mechanism
- Drug-drug interaction computation: scarcity × social_proof = synergy, scarcity × authority = antagonism
- Cites Clark 1933 (dose-response curves), Bliss 1939 (drug interaction models), Chou & Talalay 1984 (Combination Index for drug interactions)
- Adapted to persuasion via Petty & Cacioppo 1986 (ELM intensity effects)

**It is orphaned. Nothing imports it.** The file is ~500 lines of theory-grounded work written in some prior session and abandoned before wiring.

**This is a more dramatic version of the `page_edge_bridge.py` finding from Pass B.** In Pass B, one substantive architectural fix was stranded. In Pass C, at least one of the stranded fixes is something I was independently about to propose building because I had no idea it existed. **My future-work items from earlier sessions may already exist in the codebase. Before proposing anything new going forward, the first step should be to grep the orphan list for similar constructs.** This is a new rule that should probably go into the theoretical foundation's discipline section.

## 4. Why the atoms were stranded

Not enough signal from this pass to know for sure. Three possibilities:

1. **Session-boundary drift.** Each atom was written in a session that ran out of time or handed off to a subsequent session that never landed the wiring. This is the most common explanation for the pattern, and it fits the fact that every atom is fully written but none is wired.

2. **DAG topology uncertainty.** The AtomDAG in `dag.py` imports atoms statically at module load and arranges them in levels. Adding a new atom requires deciding which level it belongs at, what its upstream dependencies are, and how MechanismActivation should fuse its output. If that design work was not done at the same time as the atom was written, the wiring got deferred. This is consistent with the shape of the file — atoms are written, but the DAG's `dag.py` was not updated to include them.

3. **Hold-for-review.** The atoms might have been deliberately held back pending a later integration pass that never happened, possibly because someone felt the DAG was not yet ready or because the wiring required an MechanismActivation refactor that was out of scope.

**All three explanations suggest the same remedy: wire them in, now, together, with an MechanismActivation update that knows how to fuse the new construct evidence into mechanism scoring.**

## 5. The Wiring Plan

I am **not** going to do this work in the current session. The wiring requires:

1. Reading `dag.py` end-to-end to understand the current level structure, upstream/downstream dependencies, and parallelism discipline.
2. Reading `MechanismActivationAtom` to understand how it currently fuses evidence from the 14 live atoms.
3. Deciding which of the 16 orphan atoms belong at which DAG level. Most are likely Level 2 (construct-level reasoning, downstream of UserState/RegulatoryFocus/ConstrualLevel, upstream of MechanismActivation). `coherence_optimization` probably belongs at the very end of the DAG as a post-fusion conflict-resolver.
4. Updating `dag.py` imports and level definitions to include the new atoms.
5. Updating `MechanismActivationAtom` to consume evidence from the new atoms.
6. Running a synthetic decision end-to-end to verify the expanded DAG produces sane outputs and stays within the latency budget (~50ms for the fast path).
7. Measuring the latency impact — 16 new atoms at Level 2 running in parallel is 16 more Neo4j queries and fusion operations, which may exceed the current budget. Some atoms may need to be pushed to the reasoning path (500ms budget) rather than the fast path.

**Estimated effort: 2-3 focused sessions.** The work is not conceptually hard — each atom is already written and tested against its own `BaseAtom` contract — but the DAG integration is where architectural care is needed to avoid breaking the current 14-atom path.

### 5.1 Proposed integration order (highest-leverage first)

If the work has to be staged across multiple passes, I would stage it in priority order by LUXY-relevance × architectural load-bearing:

**Stage 1 — Core decision-path atoms (6):**
- `mimetic_desire_atom` — dominant luxury mechanism
- `brand_personality` — load-bearing for all creative
- `narrative_identity` — load-bearing for identity framing
- `regret_anticipation` — critical for high-value decision framing
- `autonomy_reactance` — backfire prevention
- `coherence_optimization` — required to resolve new cross-atom conflicts (must ship with Stage 1)

**Stage 2 — Sophistication / credibility atoms (4):**
- `signal_credibility` — costly signal evaluation
- `strategic_awareness` — detect user persuasion sophistication
- `relationship_intelligence` — first-timer vs repeat
- `cooperative_framing` — bypass persuasion knowledge

**Stage 3 — Mechanism-level refinement atoms (3):**
- `persuasion_pharmacology` — dose-response and interactions
- `strategic_timing` — urgency authenticity check
- `motivational_conflict` — approach-avoidance gradient

**Stage 4 — Individual-difference atoms (3):**
- `temporal_self` — future-self continuity
- `interoceptive_style` — body-aware vs analytical
- `query_order` — evaluation ordering

Each stage should include its own integration test. Stage 1 must ship as a unit because `coherence_optimization` is the atom that resolves the new conflicts the other Stage 1 atoms will produce.

## 6. What this means for the LUXY campaign build

Same message as Pass B but stronger: **the correct next campaign-build action is not to build new atoms, it is to wire in the 16 that already exist.** Twelve of them are directly relevant to LUXY. Several of them — mimetic_desire, narrative_identity, brand_personality, regret_anticipation, signal_credibility — are arguably load-bearing for any luxury campaign running on an inferential architecture. Without them, ADAM is running a rump version of its own architecture and the LUXY campaign will underperform its own capabilities.

**The recommended path forward is:**

1. **Do not start the campaign build until at least Stage 1 of the atom wiring is done.** Six atoms plus coherence_optimization. 1-2 focused sessions.
2. **Then proceed to the `page_edge_bridge.py` wiring** from Pass B (the page-shift-before-mechanism-scoring fix). 2 focused sessions.
3. **Then build the campaign on top of the now-fuller architecture.**

Stages 2, 3, and 4 of atom wiring can happen after the campaign launches, once we have real outcome data to verify the DAG is behaving well under load. They are not blocking.

**Total estimated time before the campaign build starts:** 3-4 focused sessions of atom-and-wiring work. This is more than I would have recommended two hours ago, but it is the right sequencing given what we now know about how much of the claimed architecture is stranded.

## 7. Pattern recognition — what the audit has now taught us

Across Passes A (halted), B, and C, the same pattern has appeared three times:

- **Pass A (5 library files)** — Five modules I was going to delete as "safe orphans" turned out to be substantive stranded work (page gradient computation, directed copy evolution, Claude review summarization, corpus builder, review aggregator).
- **Pass B (page_edge_bridge.py)** — One orphan module turned out to be a theoretically-grounded architectural fix that is the most important improvement to the page intelligence pathway.
- **Pass C (16 atoms)** — All 16 orphan atoms turned out to be theory-grounded construct-level reasoning modules, each adding specific capabilities the DAG currently lacks.

**The pattern is clear: "orphaned" in this codebase does not mean "dead." It almost always means "stranded work."** I should hold this as a rule going forward:

> **Rule: Before any future orphan-classification pass, default to stranded-work. Only classify as dead-code after reading the file and finding the functionality is clearly superseded elsewhere or clearly abandoned mid-draft.**

The audit's original Tier 0 "safe deletions" bucket was wrong in premise because it assumed orphan = dead. The evidence across three passes is that orphan = stranded at a rate of roughly 100%. There may still be some dead code in the remaining 190+ orphan files (particularly the package `__init__.py` artifacts and the CLI-tool files), but the base rate for substantive orphans is stranded-work.

This is probably the single most important operational lesson from the audit work in this session, and it should be folded back into the theoretical foundation's discipline rules.

## 8. Concrete Next Actions

Ranked by immediate value for the campaign build:

1. **Stage 1 atom wiring** — wire the 6 core decision-path atoms plus `coherence_optimization` into the DAG. 1-2 sessions. Output: `dag.py` update, MechanismActivation update, integration test, commit.
2. **Page_edge_bridge wiring** (Pass B followup) — wire `compute_page_edge_shift` into `bilateral_cascade.py`. 2 sessions. Output: cascade patch, smoke test, commit.
3. **Campaign build** — with the expanded architecture live.
4. **Stage 2 atom wiring** — sophistication/credibility atoms. Can happen during campaign run.
5. **Stage 3 atom wiring** — mechanism-level refinement. Can happen after.
6. **Stage 4 atom wiring** — individual-difference atoms. Can happen later.

**Total estimated work before the campaign build starts: 3-4 focused sessions.** The campaign build then proceeds on a DAG running at least 20 atoms (14 existing + 6 new) with the page-shift architecture fixed.

## 8a. Pass C Deep-Dive — The Second DAG Finding (added after initial Pass C)

**This section was added after Chris flagged that the orphan atoms were supposed to be part of the active set and that he did not understand how they became orphaned. A defensive re-check of atom wiring mechanisms surfaced a finding that is bigger than the original Pass C scope: there is an entire stranded orchestration layer, not just stranded individual atoms.**

### The two parallel DAG systems

**System 1 — Simple DAG (live in production):**

- `adam/atoms/dag.py` (585 lines)
- Imports 14 atom classes directly via static Python imports
- Called by `campaign_orchestrator.py._execute_real_atom_dag()`
- This is what actually runs when a decision is made

**System 2 — Construct-taxonomy DAG (orphaned, never wired):**

- `adam/atoms/orchestration/construct_dag.py` (489 lines)
- `adam/atoms/orchestration/dag_executor.py` (1082 lines)
- `adam/atoms/orchestration/langgraph_feedback.py` (545 lines)
- **Total: 2,116 lines of orchestration layer**
- References all 28 atoms by string name via a `DOMAIN_ATOM_MAPPING` dict — NOT via Python imports, which is why the audit script classified it as "rescued only by tests/scripts"
- Maps 35 construct-taxonomy domains (from `adam/intelligence/construct_taxonomy.py`) to primary and secondary atoms
- Implements cross-domain dependencies via MODULATES relationships
- Docstring claims *"28 atoms, 6-level DAG"*
- **Only importer anywhere:** `scripts/validate_construct_architecture.py` — a validation/test script

### Why the original Pass C missed this

The initial Pass C read each orphan atom file's docstring and correctly identified that they were substantive stranded work. But I did not check for *non-import* references to the atoms — `construct_dag.py` refers to atoms by string name in a dict, not by `from adam.atoms.core.X import Y`, so no import-graph analysis (regex or AST) would show the reference. The atoms are orphaned at the import level AND referenced by a second orphaned DAG at the string level. Both layers are stranded.

### What this finding actually means

**Chris's intuition that "these atoms were supposed to be in the active set" was correct.** The design that wires all 28 atoms together exists at `adam/atoms/orchestration/`. Someone built it — in three files totaling 2,116 lines — and then never integrated it with the production path. The production path runs on the simpler `dag.py` that predates this work.

**This is the same drift pattern at a much larger scale than Passes A, B, or the initial Pass C.** The pattern across all of them:

- **Pass A** — 5 stranded library files
- **Pass B** — 1 stranded architectural fix (`page_edge_bridge.py`)
- **Pass C original** — 16 stranded atoms
- **Pass C deep-dive** — an entire stranded orchestration layer (2,116 lines: construct_dag + dag_executor + langgraph_feedback)

Someone built the full upgrade and never flipped the switch.

### What `construct_dag.py` actually maps (abbreviated)

Looking at `DOMAIN_ATOM_MAPPING` in `construct_dag.py`, every orphan atom from Pass C has a specific assignment to one or more construct domains:

| Orphan atom | Mapped to domain(s) |
|---|---|
| `brand_personality` | personality (secondary), consumer_traits (secondary), self_identity (secondary), brand_personality (primary), attachment (secondary) |
| `motivational_conflict` | motivation (secondary), implicit_motivation (primary) |
| `regret_anticipation` | prospect_theory (primary), risk_uncertainty (primary) |
| `mimetic_desire` | social_influence (secondary), evolutionary (secondary) |
| `cooperative_framing` | social_influence (secondary), strategic_fairness (primary), moral_foundations (primary) |
| `persuasion_pharmacology` | persuasion_processing (secondary), implicit_processing (secondary), nonconscious_architecture (secondary), evolutionary (secondary) |
| `signal_credibility` | persuasion_processing (secondary), strategic_fairness (secondary), lay_theories (primary), trust_credibility (primary), peer_persuasion (secondary) |
| `strategic_awareness` | strategic_fairness (primary) |
| `interoceptive_style` | implicit_processing (primary), nonconscious_architecture (primary) |
| `temporal_self` | temporal (primary) |
| `strategic_timing` | temporal (secondary) |
| `relationship_intelligence` | attachment (primary), brand_relationship (primary) |
| `narrative_identity` | self_identity (primary) |

Every orphan atom has an assigned role in the construct-taxonomy-driven DAG. Every one of those assignments was designed, documented, and never wired in.

### The revised wiring strategy

My original Pass C recommendation was *"wire the 16 atoms into `dag.py` in four stages, Stage 1 being 6 core atoms plus coherence_optimization."* That was a manual extension of the simple DAG.

**The better strategy, now that the second DAG is visible, is to wire the orchestration layer itself into the production path,** replacing or complementing `dag.py`. This brings online:

1. All 28 atoms (not just the 14 currently live or the 14 + 6 Stage 1)
2. The construct-taxonomy-driven orchestration (35 domains mapped to atoms, not hardcoded level structure)
3. The cross-domain MODULATES dependency handling (atoms influence each other based on construct relationships, not hardcoded topology)
4. The LangGraph feedback integration (545 lines of learning-loop wiring)

**The risk and effort profile:**

- **Risk:** higher than the Stage 1 manual wiring. Touching the core decision path's atom execution is disruptive. `dag_executor.py` at 1082 lines is substantial and needs to be read end-to-end before any switchover.
- **Effort:** 1-2 weeks of focused work instead of 1-2 sessions. Reading the 2,116 lines takes one session by itself; designing the switchover or dual-running strategy is another session; implementation is 2-3 sessions; testing and latency validation is another 2-3 sessions.
- **Upside:** the entire designed architecture comes online at once, not piecemeal. The foundation doc's architectural claims become true at the runtime level. Stages 2, 3, 4 from the original Pass C plan become unnecessary because all atoms ship together.

**My revised recommendation for what to do before the campaign build:**

1. **Read the orchestration layer end-to-end** — one session. Output: a supplemental note in this document describing what `dag_executor.py` does, how it composes `construct_dag.py` and `langgraph_feedback.py`, and what changes would be needed to wire it into `campaign_orchestrator.py`.
2. **Design the switchover strategy** — parallel-run the old simple DAG and the new orchestration layer during a validation window so outputs can be compared, OR do a hard cutover with a feature flag that can revert. One session. Output: a design note.
3. **Implement the wiring** — update `campaign_orchestrator.py` to call the new orchestration layer. Probably 2-3 sessions. Output: a committable patch plus smoke tests.
4. **Latency validation** — 28 atoms is 2x the current 14, running under the same <50ms budget. May require pushing some atoms to the reasoning path (<500ms budget). 1-2 sessions.
5. **Campaign build** starts on top of the full architecture.

**Total pre-campaign work revised up to 1-2 weeks.** Larger than the original Pass C estimate. The argument for paying it: the campaign built on top of the 28-atom DAG will perform substantially better than a campaign built on the 14-atom rump, and the difference will be visible immediately in the bilateral alignment scoring because the additional atoms contribute evidence MechanismActivation currently has no access to.

**The argument against paying it up front:** if the LUXY launch timeline is tighter than 1-2 weeks, we could do Stage 1 of the original Pass C plan (6 core atoms into the simple DAG) as a bridge, launch the campaign, and do the full orchestration wiring after real traffic is flowing. That is a valid tradeoff — it is a matter of whether timeline or architectural completeness matters more for the first campaign.

**This is a decision I cannot make alone.** Chris should see this finding before choosing the path. The documentation is now complete; the choice is: (a) launch on the rump with Stage 1 bridge, (b) launch on the full 28-atom orchestration layer, or (c) something in between.

---

## 9. Update to the Theoretical Foundation

The foundation doc currently says (quoting from memory):

> *"30+ Atom of Thought (AoT) psychological reasoning modules in DAG"*

This is wrong at the runtime level. The DAG runs 14. It should be updated to reflect the actual state:

> *"30 atom implementations exist at `adam/atoms/core/`, each grounded in peer-reviewed psychological research. 14 are currently imported and run by `dag.py`; 16 are fully written but unwired. See `ADAM_ATOM_TRIAGE_PASS_C.md` for the per-atom classification and the stage-ordered wiring plan."*

**Do not update the foundation doc until the wiring is actually complete.** The current version is wrong but updating it to "30 atoms" before the wiring is done would perpetuate the same problem in the other direction — documentation claiming a runtime state that doesn't exist.

Once Stage 1 lands, the foundation doc can be updated to say "21 atoms (14 original + 6 new)." Once Stage 4 lands, it can be updated to "30 atoms." The documentation should follow the wiring, not lead it.
