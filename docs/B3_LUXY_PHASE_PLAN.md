# B3-LUXY Phase Plan — Atom Redo + Chain-Attestation Primitive + L3 Integration

**Status:** Active spec, committed 2026-04-27. Canonical reference for the atom-redo work that ships theoretical depth as the LUXY pilot's differentiation moat.
**Decision:** [`memory/project_atom_audit_and_path_b_decision.md`](../memory/project_atom_audit_and_path_b_decision.md)
**Discipline rule:** [`memory/feedback_atom_redo_discipline.md`](../memory/feedback_atom_redo_discipline.md)
**Foundation §:** `ADAM_THEORETICAL_FOUNDATION.md` §4.3 (drift pattern: computing assessments instead of producing reasoning chains)

---

## 1. Strategic frame

Chris's reaffirmation, 2026-04-27: *"If we are going to do it for the pilot, we might as well do it the way it was supposed to be done. Fully create it for the LUXY campaign; if it proves strong and useful, then consider recreating it for the entire system."*

Three commitments follow:

1. **Pilot is the only path forward.** Every Phase 0–3 deliverable is justified by per-atom contribution measurable on LUXY pilot data. The pilot's job is the investor narrative — half-measures don't serve it.
2. **Generalization is post-pilot.** The 8 wrappers deferred from this scope and the 4 C-atoms deferred to post-pilot Path B do *not* get touched until LUXY pilot data validates the approach. Validate first, then expand.
3. **Discipline rule binds every redo.** A redone atom that misses any of (a)+(b)+(c) stays a wrapper with the honest "theory-in-docstring" tag. No partial implementations dressed as proper. The orientation document was written because that drift pattern shipped before; the rule is the structural defense against re-running it while ostensibly fixing it.

---

## 2. The 9 atoms in scope

### 2a. Already-novel C-class — chain-attestation work only (formulas exist in code)

| Atom | Canonical theory | LUXY load-bearing because |
|---|---|---|
| `autonomy_reactance.py` | Brehm 1966; Brehm & Brehm 1981; Steindl et al. 2015 (intertwined model) | Luxury buyers backfire on coercive mechanisms — reactance is the safety valve |
| `mimetic_desire_atom.py` | Girard *Deceit, Desire, and the Novel*; model-based desire + rivalry-risk | Luxury IS mimetic; model selection is first-order causal |
| `strategic_awareness.py` | Friestad & Wright 1994 Persuasion Knowledge Model | Luxury buyers detect tactics; detectability penalty is real |
| `persuasion_pharmacology.py` | Hill equation dose-response; tolerance / down-regulation; therapeutic window | Repeat-exposure tolerance dynamics in retargeting sequences |
| `temporal_self.py` | Parfit *Reasons and Persons*; Hershfield 2011 future-self continuity | Luxury purchases activate future-self projection |

### 2b. Currently-wrapper atoms — engineering redo against canonical formulas

| Atom | Canonical formula source | LUXY load-bearing because |
|---|---|---|
| `signal_credibility.py` | Spence 1973 §2 (job-market signaling); Zahavi 1975 (handicap principle): `c_L > b > c_H` separating equilibrium | Price IS the signal in luxury — extremely load-bearing |
| `regret_anticipation.py` | Loomes & Sugden 1982 eq. 4: `RT(action, outcome) = u(outcome) + R(outcome − foregone)` | Luxury purchases are regret-loaded |
| `ambiguity_attitude.py` | Ellsberg 1961: ambiguity premium = `(knownEU − unknownEU) / unknownEU` | Premium pricing tolerance requires ambiguity tolerance |
| `regulatory_focus.py` | Higgins 1997; Higgins et al. 2001 RFQ instrument | Shapes luxury framing (prevention vs promotion-aspiration) |

### 2c. Explicitly out of scope for B3-LUXY

- **4 C-atoms deferred to post-pilot Path B** (novel but not LUXY-load-bearing): `query_order`, `cooperative_framing`, `predictive_error`, `decision_entropy`.
- **13 wrappers deferred** (no clear canonical formula or weak luxury relevance): `narrative_identity`, `interoceptive_style`, `motivational_conflict`, `cognitive_load`, `construal_level`, `personality_expression`, `message_framing`, `channel_selection`, `user_state`, `ad_selection`, `relationship_intelligence`, `information_asymmetry`, `strategic_timing`. Some may eventually warrant redo or honest retirement; out of scope until LUXY pilot validates the approach.

---

## 3. Discipline rule (a)+(b)+(c)+(d) — binds every redo commit

**(a) Canonical formula in code with `paper:section` citation in source comment header.**
- `# Spence 1973 §2.3: c_L > b > c_H separating equilibrium`
- `# Loomes & Sugden 1982 eq. 4: RT(action, outcome) = u(outcome) + R(outcome − foregone)`
- `# Brehm & Brehm 1981 §3: R = f(I × M × P) — multiplicative in importance × magnitude × propagation`

**(b) Regression tests pinning published anchors.** The paper's stated boundary cases, edge cases, and canonical inequalities are testable invariants.
- `test_loomes_sugden_zero_outcome_zero_regret` pins RT(0,0)=0 boundary
- `test_ellsberg_known_minus_unknown_premium_positive` pins paradox direction
- `test_spence_separating_equilibrium_inequality` pins `c_L > b > c_H`
- `test_brehm_reactance_monotonic_in_threat_magnitude` pins monotonicity in M
- `test_brehm_reactance_zero_when_freedom_unimportant` pins I=0 → R=0

**(c) Explicit calibration-pending flag** where empirical constants aren't yet pilot-derived. Placeholders documented AS placeholders with stated retirement trigger:
- `A14: SPENCE_COST_CURVES_PILOT_PENDING — handicap cost curves use literature midpoints; retire when LUXY pilot accumulates ≥500 conversions per status-tier`
- `A14: REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING — I/M/P weights from Steindl 2015 meta-analysis midpoints; retire when LUXY pilot accumulates ≥200 backfire events`

**(d) Anything missing (a)+(b)+(c) stays a wrapper with honest "theory-in-docstring" tag.** No partial implementations shipped as proper. The wrapper version is honest about being a weighted-sum scaffold; the partial-implementation version is dishonest about being a theoretical primitive.

**PR review checklist:**
1. Canonical formula with `paper:section` citation present at the formula?
2. Regression tests pinning published anchors present and passing?
3. Placeholder constants flagged with calibration-pending A14 entries?
4. If any of those failed, does the atom remain a wrapper with the honest tag?

If any commit doesn't pass this checklist, it's drift and the discipline anchor failed.

---

## 4. Chain-attestation primitive — design intent

The primitive materializes the foundation §4.3 commitment that atoms emit *the chain of construct activations that produced the scalar*, tagged with the literature grounding each link, consumed downstream as chain (not scalar).

### 4.1 What an atom currently emits

Today's `AutonomyReactanceAtom._build_output()` returns `AtomOutput.secondary_assessments` as an untyped `Dict[str, Any]` — `reactance_profile`, `mechanism_adjustments`, `reactance_budget`, `mechanisms_to_avoid`, `hard_constraints`. The chain that produced these — *user has high persuasion knowledge → lowers reactance threshold → increases backfire probability for high-coerciveness mechanisms* — exists in the code's logic but is never materialized.

### 4.2 What chain-attestation adds

Each atom emits a typed `ChainAttestation` alongside the existing `AtomOutput` (additive, not breaking). The attestation contains:

```
ChainAttestation(
    atom_id, request_id, target_construct,
    chain: List[ConstructLink]              # ordered links; each grounds in a paper:section
        ConstructLink(
            source_construct, relation_type, target_construct,
            evidence_value, confidence,
            citation: "paper:section",
            calibration_status: pinned | pilot_pending,
        )
    final_assessment: TypedEvidence         # scalar with provenance
    mechanism_adjustments: Dict[mechanism_id, AdjustmentEvidence]
        AdjustmentEvidence(
            adjustment_value,
            chain_links_responsible: [link_id, ...]    # which chain steps drove this
            confidence,
        )
    provenance: ChainProvenance              # atom version, formula hashes, timestamp
)
```

### 4.3 What L3 does with it

L3 consumes chain-attestations as additional alignment dimensions alongside the existing 21 bilateral edge dims (`bilateral_cascade.py:961` `level3_bilateral_edges` — 7 core + 13 extended + the 21st metaphor dim from F1–F5). The chain-derived dims are NOT a replacement for bilateral edges — they are an additional signal source. The graph edge says "this archetype historically converted on this product-side construct"; the chain-attestation says "for this specific decision, the user-side reasoning chain produced these mechanism adjustments because of these documented theoretical links."

Both feed into mechanism scoring. Both update independently in the learning loop — graph edges update on outcome, chain links update on outcome via TheoryLearner's `LinkPosterior` (see foundation §4.4: theory-revision update vs measurement-error update).

### 4.4 What learning does with it

When an outcome arrives, the OutcomeHandler routes per-link feedback to TheoryLearner:
- *Did the predicted construct-link hold for this user/decision?* → `LinkPosterior` update for that specific (source → relation → target) triple.
- *Did the chain composition produce the right mechanism adjustment?* → `ChainOutcomeRecord` update for the specific chain shape.

The per-link breakdown is what makes per-atom contribution measurable on LUXY pilot data — see §6.

### 4.5 Emergent design discipline

The primitive is **emergent from `autonomy_reactance` as the simplest chain shape** (single-source threat → threshold modulation → mechanism penalty). It will be refactored as atoms 2–3 come in and reveal additional chain shapes (multi-source convergence, recursive composition, etc.). After atom 3, the schema locks as canonical and remaining 6 atoms slot in.

This is intentional. Designing the primitive in the abstract before any atom uses it produces the wrong abstraction. Designing it from the simplest concrete case and refactoring twice produces the right one.

---

## 5. L3 integration interface

**File:** `adam/api/stackadapt/bilateral_cascade.py` — function `level3_bilateral_edges` at line 961.

**Current state:** Reads 7 core + 13 extended + 1 metaphor = 21 bilateral edge dimensions per `(asin, archetype)` pair. Computes mechanism scoring from these.

**Phase 0 change:** Add parameter `chain_attestations: Optional[List[ChainAttestation]] = None`. When present, derive per-mechanism contribution from the union of chain-attestations across all atoms that ran for this decision, AND from the existing 21 bilateral dimensions. The two contributions combine multiplicatively (not additively — additive smears, multiplicative respects chain-dependent attenuation).

**Pseudocode (final shape determined during deliverable 4):**

```
edge_score = score_from_bilateral_dimensions(edge_agg)                # existing path
chain_score = score_from_chain_attestations(chain_attestations)        # new path
combined = edge_score × chain_score_modifier                            # multiplicative
```

**A14 flag:** `CHAIN_ATTESTATION_LUXY_FUSION_FORM_PILOT_PENDING — multiplicative fusion form is the prior; pilot data may indicate weighted-additive or chain-dim-as-21st-additional-dim works better.` Retires when pilot accumulates ≥1000 decisions with both signal types active.

---

## 6. Per-atom contribution measurement framework

The pilot's job is to validate: **does each redone atom contribute measurable prediction lift on LUXY pilot data?**

For each atom, three measurements:

1. **Prediction-correctness lift.** With/without the atom's chain-attestation in the L3 fusion, what is the delta in conversion-prediction AUC against held-out pilot data? Atom is "useful" if delta > 0.01 AUC at 95% CI.
2. **Chain-link survival.** Per `LinkPosterior` update, what fraction of the atom's theoretical links survived (posterior mean > 0.5) after pilot data? Atom is "theoretically grounded by data" if ≥75% of links survive.
3. **Mechanism-adjustment direction match.** When the atom recommends suppressing a mechanism and L3 follows, do those decisions have lower backfire rates (regret signals) than counterfactual decisions where L3 didn't follow? Atom is "directionally correct" if backfire rate is lower with statistical significance.

**Decision tree post-pilot:**
- All 9 atoms pass all 3 measurements → **expand to remaining 4 deferred C-atoms + start audit of 13 wrappers** (full Path B for the system).
- 5–8 atoms pass → **expand selectively to atoms in adjacent theoretical neighborhoods** (e.g., if `regret_anticipation` passes strongly, audit `prospect_theory` wrappers next).
- <5 atoms pass → **stop, deeply investigate the failures**, do not expand. Failure mode is informative — measurement-error vs theory-revision distinction (foundation §4.4) determines whether to refine atoms or revise the architecture.

The decision is data-driven, not narrative-driven. The pilot answers it.

---

## 7. A14 calibration-pending registry (Phase 0 entries)

| Constant | Where | Retirement trigger |
|---|---|---|
| `THEORY_IN_DOCSTRING_BOILERPLATE_IN_IMPL` | Audit-level | A16-class audit identifies remaining 13 wrapper atoms; each implemented properly OR explicitly retired with honest "boilerplate scaffold" docstring |
| `REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING` | `autonomy_reactance.py` | LUXY pilot accumulates ≥200 backfire events with reactance-threshold predictions |
| `MECHANISM_COERCIVENESS_LITERATURE_MIDPOINTS_PILOT_PENDING` | `autonomy_reactance.py` `MECHANISM_COERCIVENESS` dict | Pilot accumulates ≥50 conversions per mechanism with reactance-attenuated scoring |
| `SPENCE_COST_CURVES_PILOT_PENDING` | `signal_credibility.py` | Pilot accumulates ≥500 conversions per status-tier |
| `LOOMES_SUGDEN_REVERSIBILITY_WEIGHTS_PILOT_PENDING` | `regret_anticipation.py` | Pilot accumulates ≥300 conversions with regret-anticipation predictions |
| `ELLSBERG_AMBIGUITY_PREMIUM_PILOT_PENDING` | `ambiguity_attitude.py` | Pilot accumulates ≥300 conversions with ambiguity-premium predictions |
| `HIGGINS_RFQ_PILOT_PENDING` | `regulatory_focus.py` | Pilot accumulates ≥500 conversions per archetype with RFQ-derived framing |
| `CHAIN_ATTESTATION_LUXY_FUSION_FORM_PILOT_PENDING` | `bilateral_cascade.py:level3_bilateral_edges` | Pilot accumulates ≥1000 decisions with both bilateral and chain signals active |

Each entry has explicit retirement trigger. None is a permanent compromise.

---

## 8. Phase sequence + timeline

Total committed timeline: **~3.5–6.5 months pre-pilot launch**, with the 11 LUXY campaigns continuing during the build window. Pilot reporting at end has the new architecture operating on accumulated data.

### Phase 0 — Chain-attestation primitive design (~2 weeks)

Four deliverables, executed in order:

| Deliverable | Files | Status |
|---|---|---|
| 1. `docs/B3_LUXY_PHASE_PLAN.md` | this file | committed 2026-04-27 |
| 2. Chain-attestation typed-evidence schema | `adam/atoms/models/chain_attestation.py` | TBD |
| 3. `autonomy_reactance` redo + regression tests | `adam/atoms/core/autonomy_reactance.py`, `tests/unit/test_autonomy_reactance_canonical.py` | TBD |
| 4. L3 chain-attestation consumption | `adam/api/stackadapt/bilateral_cascade.py:961` | TBD |

Phase 0 ships when (1)–(4) merge, all regression tests pass, and L3 demonstrably consumes a chain-attestation produced by `autonomy_reactance` for at least one synthetic test decision.

### Phase 1 — 5 novel-atom chain-attestations (~6–10 weeks)

| Order | Atom | Chain shape novelty |
|---|---|---|
| 1 | `autonomy_reactance` | Phase 0 (simplest: single-source → threshold → penalty) |
| 2 | `persuasion_pharmacology` | Multi-step temporal: dose → tolerance → therapeutic-window |
| 3 | `mimetic_desire_atom` | Multi-source: model selection + rivalry-risk |
| 4 | `strategic_awareness` | PKM detectability — feedback loop from prior exposures |
| 5 | `temporal_self` | Continuity-based regime switch — discrete state transition |

After atom 3, schema locks. Atoms 4–5 slot in without further refactors.

### Phase 2 — 4 wrapper redos (~6–12 weeks)

| Order | Atom | Why this order |
|---|---|---|
| 6 | `signal_credibility` | Most LUXY-critical; price IS the signal in luxury |
| 7 | `regret_anticipation` | Loomes & Sugden — clean canonical formula, regret-loaded purchases |
| 8 | `ambiguity_attitude` | Ellsberg — premium tolerance is ambiguity tolerance |
| 9 | `regulatory_focus` | Higgins RFQ — reframes existing prevention/promotion logic |

### Phase 3 — L3 integration + learning-loop wire (~2–4 weeks)

- L3 consumption finalized across all 9 atoms (Phase 0's deliverable 4 was the scaffold)
- OutcomeHandler routes per-link feedback to TheoryLearner.LinkPosterior
- ChainOutcomeRecord update path live
- Per-atom contribution measurement framework wired and producing dashboards

---

## 9. Post-pilot generalization gate

Once pilot reports, the §6 decision tree determines next steps. Until then, the 8+4 deferred atoms do **not** get touched. The discipline rule against premature generalization is the same discipline rule against premature shipping: don't generalize on theory; generalize on validated theory.

---

## 10. Pointers

- `ADAM_THEORETICAL_FOUNDATION.md` §4.3 — chain-attestation rationale (the structural diagnosis this plan answers)
- `ADAM_THEORETICAL_FOUNDATION.md` §4.4 — theory-revision vs measurement-error update (what learning loop must distinguish)
- `adam/core/learning/theory_learner.py` — existing `LinkPosterior` and `ChainOutcomeRecord` infrastructure (Phase 3 integration target)
- `adam/atoms/models/atom_io.py` — existing `AtomOutput`; chain-attestation slots in additively, not replacing
- `adam/api/stackadapt/bilateral_cascade.py:961` — `level3_bilateral_edges`; the 21-dim consumption point chain-attestations augment
- `memory/feedback_atom_redo_discipline.md` — the (a/b/c/d) discipline rule
- `memory/project_atom_audit_and_path_b_decision.md` — the B3-LUXY decision context
