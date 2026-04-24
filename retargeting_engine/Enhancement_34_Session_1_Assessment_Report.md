# Enhancement #34: Session 34-1 Assessment Report
## Methodological Power Upgrade — Reality vs. Specification
## Date: March 26, 2026

---

## How to Read This Report

For each of the 8 upgrade categories, this report answers:
1. **What the directive proposes** (from the spec)
2. **What the codebase actually has** (from reading every file)
3. **Where assumptions hold and where they break**
4. **Recommended action** (Build / Modify / Skip / Defer)
5. **Adjusted implementation priority**

---

## CATEGORY 1: MECHANISM SELECTION (BANDITS)

### What the Spec Assumes
> "Context-free Thompson Sampling with Beta-Binomial. Completely ignores 157 psychological dimensions."

### What Actually Exists

**Three Thompson Sampling systems, not one:**

| System | File | Context Used | Arms |
|--------|------|-------------|------|
| Meta-Learner Thompson | `adam/meta_learner/thompson.py` | 13 features (buyer_uncertainty, interaction_count, data_richness, etc.) | 8 learning modalities (not mechanisms) |
| Cold Start Thompson | `adam/cold_start/thompson/sampler.py` | Archetype membership only | ~10 cognitive mechanisms per archetype |
| **Retargeting Thompson (NEW)** | `adam/retargeting/engines/prior_manager.py` | (mechanism, barrier, archetype) triple at 5 hierarchy levels | 16 therapeutic mechanisms × 10 barriers × 8 archetypes |

**The spec's assumption is PARTIALLY correct:**
- The meta-learner Thompson IS nearly context-free (13 dims, not 157)
- The cold-start Thompson IS archetype-only
- BUT the retargeting hierarchical prior manager (Enhancement #33, just built) IS contextual — it conditions on barrier × archetype × campaign, which is FAR more context than the spec assumes exists

**The 157-dim context (65 buyer + 65 seller + 27 alignment) IS available** — it flows through the bilateral cascade at Level 3+. But it's used for creative parameter DERIVATION (via hand-coded derive_* functions), not for Thompson Sampling arm selection.

### Where Assumptions Break

1. **"Completely ignores 157 dimensions"** — Partially false. The retargeting Thompson conditions on (barrier, archetype), which are DERIVED from bilateral edge analysis. The 27 alignment dimensions flow into barrier diagnosis, which then conditions Thompson Sampling. It's indirect but real.

2. **"Maintains separate posterior per arm"** — True for meta-learner, but the retargeting hierarchical prior manager maintains posteriors per (mechanism × barrier × archetype × level) — ~6,400 potential cells. This IS contextual.

3. **"O(K√T) regret"** — True for the meta-learner. The retargeting system achieves Õ(d√T) implicitly because it conditions on barrier category (d effective dimensions).

### Recommendation

| Proposed | Action | Rationale |
|----------|--------|-----------|
| **Neural-LinUCB** | **BUILD (Tier 1, modified)** | The 157-dim context IS available but unused by Thompson Sampling. Neural-LinUCB would capture non-linear buyer×seller×alignment interactions that the current barrier-categorical conditioning misses. Modify: use the 43 bilateral edge dimensions (not full 157) as context, since those are what's available at inference. |
| **IDS (Information-Directed Sampling)** | **DEFER to Tier 2** | IDS's advantage is largest when mechanisms have DIFFERENT information values. We need data to assess this — run Neural-LinUCB first, then measure information gain per mechanism. If mechanisms are equally informative, IDS degenerates to Thompson Sampling. |
| **Meta-Thompson for Cold Start** | **SKIP** | Enhancement #33's hierarchical prior manager already provides cold-start handling via 5-level inheritance (new campaigns inherit from corpus → category → brand). This achieves the same goal as Meta-Thompson through a different mechanism. Implementing Meta-Thompson would duplicate functionality. |

### Key Divergence from Spec
The spec doesn't know about Enhancement #33's hierarchical prior manager. That system already solves cold-start and provides barrier-conditional context. The remaining gap is: the 43 bilateral edge dimensions available at L3+ could directly modulate mechanism selection (Neural-LinUCB), instead of being reduced to barrier categories first.

---

## CATEGORY 2: CAUSAL INFERENCE STACK

### What the Spec Assumes
> "CausalForestDML + AIPW for heterogeneous treatment effect estimation."

### What Actually Exists

**NO econml, NO CausalForestDML, NO AIPW.**

What exists:
- `adam/intelligence/causal_discovery.py` — PC algorithm (constraint-based causal graph discovery) using partial correlations with Fisher's z-test. **Never called in production.**
- `adam/intelligence/causal_learning.py` — Records `CausalObservation` to Redis circular buffer (50K max). **Observations logged but never consumed.**
- No imports of econml, dowhy, or causalml anywhere in the codebase.

### Where Assumptions Break

**The entire category's premise is wrong.** The spec says "upgrade CausalForestDML + AIPW" but neither exists. The system uses:
- Hand-coded bilateral alignment formulas (27 dimensions, research-grounded)
- Thompson Sampling for mechanism effectiveness learning
- Gradient fields (∂P/∂dimension) for optimization priorities

There is no HTE estimation, no treatment effect decomposition, no propensity scoring.

### Recommendation

| Proposed | Action | Rationale |
|----------|--------|-----------|
| **Shrinkage BCF** | **DEFER to Tier 2** | There's nothing to replace. BCF requires treatment/control groups and sufficient observations per treatment arm. The system needs to accumulate retargeting outcome data first (via Enhancement #33) before causal inference becomes meaningful. |
| **CV-TMLE** | **SKIP** | Same issue — no existing causal inference to improve. TMLE is for doubly-robust estimation, but the system doesn't do propensity scoring. |
| **Causal Mediation Analysis** | **BUILD (Tier 2, after data accumulates)** | The logged (state, action, reward) tuples from Enhancement #33 will provide the data. Once 500+ complete sequences exist, mediation analysis can decompose WHY mechanisms work (e.g., social_proof works via trust → reduced barrier, not via conformity). This is genuinely new capability. |

### Key Divergence from Spec
The spec assumes an existing causal inference stack to upgrade. In reality, the causal infrastructure is scaffolding with no active computation. The right move is to let Enhancement #33's learning loop accumulate data, THEN build causal inference on top of that data.

---

## CATEGORY 3: BILATERAL EDGE MATHEMATICS

### What the Spec Assumes
> "Point-biserial correlations between seller dimensions and binary conversion outcomes."

### What Actually Exists

**NO point-biserial correlations. NO scipy.stats in edge computation.**

The 27 bilateral alignment dimensions are computed by **hand-designed algebraic formulas** in `adam/corpus/edge_builders/match_calculators.py` (1,151 lines). Each formula encodes a specific psychological theory:

- `regulatory_fit_score`: Cesario et al. (2004) gain/loss × promotion/prevention
- `personality_brand_alignment`: Weighted Big Five × brand personality
- `emotional_resonance`: tone_match × arousal_factor × dominance_factor
- `composite_alignment`: Weighted sum of all dimensions with category multipliers

These are NOT learned from data. They are research-grounded hand-coded formulas with fixed weights (lines 919-951).

**Bilateral edge count:** ~1,492 luxury transportation edges + 47M Amazon-derived edges in Neo4j.

### Where Assumptions Break

1. **"Point-biserial correlations"** — False. No statistical correlations are computed. Alignment dimensions are algebraic formulas, not correlation coefficients.

2. **"Linear, monotonic, univariate dependence"** — Partially true. The formulas are mostly linear (weighted sums, products), but some include non-monotonic elements (e.g., `reactance_fit` flips sign based on trigger level). The formulas are univariate within each dimension but the composite is multivariate.

3. **"Cannot detect interaction effects"** — TRUE. The 27 formulas compute each dimension independently. There are no buyer×seller interaction terms (e.g., "high neuroticism × low brand trust × scarcity = negative"). Enhancement #33's gradient fields compute ∂P/∂dim with interaction terms (12 theory-driven pairs), but these are gradient field optimizations, not edge computation.

### Recommendation

| Proposed | Action | Rationale |
|----------|--------|-----------|
| **HSIC** | **BUILD (Tier 1)** | This is the highest-value assessment. HSIC can reveal non-linear dependencies in the existing 1,492+ LUXY Ride edges that the hand-coded linear formulas miss. **Critical stop condition:** if HSIC detects <5% additional dependencies vs. current formulas, non-linear effects are minimal and we document that. If >20%, the formulas need updating. |
| **Tensor CP Decomposition** | **BUILD (Tier 2)** | With 1,492 luxury edges and 47M Amazon edges, there's enough data. Tensor decomposition can discover bilateral alignment archetypes that may not match the Enhancement #33 k-means clusters. Validation opportunity. |
| **Contrastive Two-Tower** | **DEFER to Tier 3** | Requires 10K+ edges per training split. LUXY Ride has 1,492. Amazon has 47M but those are different categories. Training a two-tower on luxury transportation alone risks overfitting. Wait until more campaign data accumulates. |
| **Optimal Transport** | **SKIP** | Most mathematically elegant but least production-tested. Engineering investment not justified vs. HSIC + tensor decomposition which answer the same questions more directly. |

### Key Divergence from Spec
The spec assumes correlations that don't exist. What DOES exist is hand-coded formulas. The real question is: do those formulas miss important non-linear structure? HSIC answers that directly.

---

## CATEGORY 4: GRAPH INTELLIGENCE LAYER

### What the Spec Assumes
> "Static Neo4j Cypher queries. Cannot learn latent patterns, adapt attention weights, or predict temporal state evolution."

### What Actually Exists

**5 GDS algorithms configured, 3 actively called at inference:**

| Algorithm | Status | Called At |
|-----------|--------|----------|
| PageRank | **ACTIVE** | cascade.py line 629, prefetch |
| Louvain Community Detection | **ACTIVE** | cascade.py line 632, prefetch |
| Betweenness Centrality | **ACTIVE** | cascade.py line 635, prefetch |
| Node2Vec (128-dim embeddings) | **CONFIGURED** | Method exists in gds_algorithms.py, execution unclear |
| Node Similarity | **CONFIGURED** | Method exists, not in active decision path |

Additionally:
- `adam/intelligence/graph/gds_runtime.py` defines 5 novel edge types and query templates
- GDS results integrated into `ad_context["gds_algorithm_intelligence"]` for atoms
- Results run through thread pool to avoid blocking async event loop

### Where Assumptions Break

1. **"Static Cypher queries"** — Partially false. The system DOES use GDS algorithms (PageRank, Louvain, Betweenness) at inference time. These are not "static queries" — they compute dynamic graph properties.

2. **"Cannot learn latent patterns"** — TRUE. No graph neural networks, no learned embeddings in production. Node2Vec is configured but its execution status is unclear.

3. **"Cannot predict temporal state evolution"** — TRUE. No temporal graph networks.

### Recommendation

| Proposed | Action | Rationale |
|----------|--------|-----------|
| **Neo4j GDS FastRP baseline** | **BUILD (Tier 2)** | FastRP is the pragmatic first step before HGT. Run FastRP, compare embeddings vs. raw features for mechanism effectiveness prediction. If no improvement → skip GNN investment. |
| **HGT (Heterogeneous Graph Transformer)** | **CONDITIONAL on FastRP** | Only if FastRP shows improvement. The bilateral graph IS a natural fit for HGT (buyer nodes, seller nodes, conversion edge nodes). But the engineering investment is significant. |
| **TGN (Temporal Graph Networks)** | **DEFER to Tier 3** | Value depends on interaction density. Most advertising users have sparse histories. Simpler temporal features (recency, frequency) already captured in session_state.py. |

### Key Divergence from Spec
The spec underestimates the current graph intelligence — 3 GDS algorithms are already active. The gap is learned embeddings (Node2Vec/FastRP/HGT), not basic graph computation.

---

## CATEGORY 5: SEQUENTIAL DECISION FRAMEWORK

### What the Spec Assumes
> "Therapeutic loop implements logic as heuristic rules rather than formal optimal sequential decision process."

### What Actually Exists

**Enhancement #33 is BAYESIAN, not heuristic:**

- `ConversionBarrierDiagnosticEngine`: Computes alignment gaps from 27-dim bilateral edge, maps to 10 barrier categories
- `BayesianMechanismSelector`: Thompson Sampling per (mechanism × barrier × archetype) with personality modulation, reactance constraints, PKM phase filtering
- `HierarchicalPriorManager`: 5-level Bayesian inheritance (corpus → campaign → sequence)
- Full (state, action, reward) tuples logged per touch
- Wicklund multiplicative reactance model (not additive)
- State space: 300 states (10 barriers × 6 stages × 5 scaffolds)

### Where Assumptions Break

1. **"Heuristic rules"** — FALSE. The mechanism selection IS Thompson Sampling with learned Beta posteriors, personality modulation, and hierarchical prior inheritance. The barrier diagnosis uses alignment gap computation. The reactance model uses Wicklund's multiplicative hydraulic model.

2. **"Not formal optimization"** — PARTIALLY TRUE. It's Bayesian bandit optimization per state, but NOT a full MDP/POMDP with transition models. There's no explicit state transition probability P(s'|s,a) learned from data.

### Recommendation

| Proposed | Action | Rationale |
|----------|--------|-----------|
| **Constrained POMDP** | **DEFER to Tier 3** | The 300-state space is tractable, but POMDP requires transition models that don't exist yet. Enhancement #33's learning loop needs to accumulate enough sequences to estimate P(s'|s,a). After 500+ completed sequences, revisit. |
| **Offline RL (CQL/IQL)** | **DEFER to Tier 3** | Same prerequisite: sufficient logged sequences. The data structure IS compatible (state, action, reward tuples logged). But the data volume isn't there yet. |
| **Options Framework** | **BUILD (Tier 2)** | This is a formalization of what Enhancement #33 already does implicitly. Each TTM stage IS an option with initiation, policy, and termination. Formalizing it reduces learning horizon from 10-touch to 5-6 option policies × 2-3 touches. Low implementation cost, high structural benefit. |

### Key Divergence from Spec
The spec significantly underestimates Enhancement #33. It's already Bayesian with hierarchical learning, not heuristic rules. The remaining gap is transition model learning (MDP/POMDP), which requires more data.

---

## CATEGORY 6: PSYCHOLOGICAL ANNOTATION PIPELINE

### What the Spec Assumes
> "Zero-shot Claude with no fine-tuned models, no calibration, no uncertainty quantification."

### What Actually Exists

- `adam/intelligence/annotation_engine.py`: Claude-based dual-sided annotation with 20 anchored user-side dimensions and 66 ad-side dimensions
- Confidence metadata stored: `annotation_confidence` (0-1) and `annotation_tier` on both AnnotatedReview and ProductDescription nodes
- No explicit cost tracking
- No self-consistency or conformal prediction

### Where Assumptions Hold
1. **"No fine-tuned models"** — TRUE. All annotation is zero-shot Claude.
2. **"No calibration"** — TRUE. Confidence is stored but not validated against ground truth.
3. **"No uncertainty quantification"** — TRUE. Single annotation pass, no ensemble or self-consistency.

### Recommendation

| Proposed | Action | Rationale |
|----------|--------|-----------|
| **Self-Consistency (N=3)** | **BUILD (Tier 1)** | Simplest, highest-value improvement. 3 Claude passes with varied prompts → std dev = uncertainty estimate. This directly improves bilateral edge computation by down-weighting high-uncertainty dimensions. Cost: 3× annotation, but only needed for new annotations. Existing 54,960 annotations are sunk cost. |
| **Conformal Prediction** | **BUILD (Tier 1, alongside self-consistency)** | Requires calibration data with ground truth. Big Five has validated questionnaires (IPIP) matched to text corpora. For the 5 Big Five dimensions, conformal prediction gives guaranteed coverage. For other dimensions, self-consistency is the fallback. |
| **Hybrid LLM + Fine-Tuned** | **DEFER to Tier 2** | Knowledge distillation (Claude annotations as training data for RoBERTa) is sound but requires engineering investment. Do after self-consistency reveals which dimensions have high uncertainty (those are candidates for fine-tuning). |

---

## CATEGORY 7: COGNITIVE SCIENCE GROUNDING

### What the Spec Assumes
> "System lacks cognitive science grounding for barrier diagnosis."

### What Actually Exists

- `regulatory_fit_score`: Captures promotion/prevention orientation (Higgins)
- `spending_pain_match`: Captures loss aversion (Kahneman & Tversky)
- `SessionStateTracker`: Kalman-like updates with uncertainty-scaled gains
- Reactance model: Wicklund multiplicative hydraulic (Enhancement #33)
- **NO response time or dwell time collected at the pixel/impression level**
- **NO S-shaped prospect theory value function**

### Where Assumptions Hold
1. **"No DDM parameters"** — TRUE. No drift-diffusion model, no response time analysis.
2. **"Response time data required"** — TRUE. The system captures session_start/last_activity but NOT per-impression time-to-click or dwell duration from StackAdapt pixels.

### Recommendation

| Proposed | Action | Rationale |
|----------|--------|-----------|
| **DDM Parameters** | **BUILD (Tier 1, simplified first step)** | Full HDDM requires response time data that isn't currently captured. **Step 1:** Add time-to-click and dwell_seconds to the StackAdapt webhook event processing. **Step 2:** Once 1000+ timed observations accumulate, estimate drift rates per barrier type. Step 1 is prerequisite and low-cost. |
| **Prospect Theory Value Function** | **BUILD (Tier 2)** | The S-shaped value function is genuinely missing. Regulatory fit captures gain/loss ORIENTATION but not the asymmetric weighting (losses weighted λ≈2.25× vs gains). Adding this to the bilateral edge computation would strengthen the emotional_resonance and spending_pain dimensions. |
| **Active Inference** | **SKIP** | No published advertising applications. High implementation risk. Respect it, don't build it. |

---

## CATEGORY 8: INFORMATION-THEORETIC ARCHITECTURE

### What the Spec Assumes
> "No unified information-theoretic objective."

### What Actually Exists

- 43 bilateral edge dimensions queried at inference
- Only 20-30 actively derived into creative parameters
- Many dimensions sparse (COALESCE defaults to 0.5)
- No PCA, CCA, or dimensionality reduction
- No effective rank estimation
- Enhancement #33 adds information value bidding (∂model_accuracy/∂impression)

### Where Assumptions Hold
1. **"Components treated independently"** — TRUE. Bandit, causal, graph, annotation, retargeting are separate systems.
2. **"No dimensionality analysis"** — TRUE. No PCA/CCA anywhere.

### Recommendation

| Proposed | Action | Rationale |
|----------|--------|-----------|
| **CCA Dimensionality Analysis** | **BUILD (Tier 1)** | This is the cheapest, highest-value assessment in the entire Enhancement #34. Run CCA on the 1,492 LUXY Ride bilateral edges: buyer_dims (65) × conversion outcome + seller_dims (65) × conversion outcome. Number of significant canonical variates tells us the effective dimensionality. If <20 → system is over-parameterized and compression improves both latency and generalization. If >40 → dimensions are mostly information-bearing. **This should run in Session 34-2 alongside HSIC.** |
| **Information Bottleneck** | **CONDITIONAL on CCA** | If CCA reveals <20 effective dimensions, IB compression is justified. If >40, skip. |
| **BOED** | **DEFER to Tier 3** | Requires substantial offline training infrastructure. Interesting but premature. |
| **Unified Objective** | **USE AS NORTH STAR** | Not an implementation task — it's an assessment criterion. When evaluating any proposed upgrade, ask: "Does this increase or decrease coherence of the information-theoretic objective?" |

---

## CROSS-CUTTING FINDINGS

### Integration Conflicts Identified

| Upgrade A | Upgrade B | Conflict | Resolution |
|-----------|-----------|----------|------------|
| Neural-LinUCB | Enhancement #33 Hierarchical Prior Manager | Both select mechanisms. Which wins? | **They compose.** Hierarchical priors provide the base posterior; Neural-LinUCB modulates based on 43-dim bilateral context. Neural-LinUCB's learned representation feeds INTO the prior manager's Thompson Sampling, not replaces it. |
| HSIC | Enhancement #33 Barrier Diagnosis | If HSIC finds non-linear dependencies, barrier thresholds may need updating | HSIC results inform threshold recalibration, not replacement. Run HSIC, update ARCHETYPE_THRESHOLDS if non-linear relationships change conversion probability curves. |
| Self-Consistency Annotations | Enhancement #33 Retargeting Learning | If annotation uncertainty is high, retargeting posteriors should weight outcomes by annotation quality | **Synergy.** Self-consistency uncertainty feeds directly into the bilateral edge computation weight, which feeds into barrier diagnosis quality. Higher-quality diagnosis → better mechanism selection → faster learning. |

### Synergies Not in Spec

1. **HSIC + Gradient Fields**: Enhancement #33's gradient fields compute ∂P/∂dim. HSIC can reveal which dimensions have non-linear response surfaces where the gradient estimate is unreliable. Use HSIC to FLAG dimensions needing non-linear gradient estimation.

2. **CCA + Hierarchical Prior Manager**: If CCA reveals effective dimensionality is <20, the prior manager's 5-level hierarchy can be compressed. Instead of (mechanism × barrier × archetype × level), compress barrier × archetype into the CCA-derived effective dimensions.

3. **DDM Timing + Retargeting Suppression**: Once time-to-click is captured, the SuppressionController can use click latency as a reactance proxy (slower clicks = increasing resistance) instead of relying solely on CTR.

### Latency Impact Assessment

| Upgrade | Path | Budget | Estimated Cost | Verdict |
|---------|------|--------|---------------|---------|
| Neural-LinUCB forward pass | Segment targeting | <100ms | ~15-25ms | **FITS** (with 43-dim context, not 157) |
| HSIC computation | Batch only | Offline | Minutes | **N/A** (not real-time) |
| Self-consistency N=3 | Batch annotation | Offline | 3× cost | **Budget question, not latency** |
| CCA dimensionality | Batch analysis | Offline | Seconds | **N/A** |
| DDM timing features | Webhook processing | <10ms added | ~1ms | **FITS** |
| Options Framework | Retargeting sequence | <200ms | ~5ms | **FITS** |

---

## RECOMMENDED SESSION SEQUENCE (REVISED)

### Tier 1: Immediate (Sessions 34-2 through 34-6)

| Session | What | Why First |
|---------|------|-----------|
| **34-2** | HSIC bilateral edge analysis + CCA dimensionality | Two diagnostic tests that determine what else to build. If HSIC shows <5% new dependencies, Category 3 is mostly done. If CCA shows <20 effective dims, compression is high priority. |
| **34-3** | Neural-LinUCB with 43-dim bilateral context | Biggest mechanism selection improvement. Uses context that currently flows through the cascade but is ignored by Thompson Sampling. |
| **34-4** | Self-consistency (N=3) + conformal prediction for Big Five | Cheapest annotation quality improvement. Directly strengthens bilateral edge computation. |
| **34-5** | DDM timing feature capture + webhook enrichment | Prerequisite for cognitive grounding. Low implementation cost (add fields to webhook). Enables future DDM estimation. |
| **34-6** | Options Framework formalization of TTM stages | Low cost, high structural benefit. Formalizes Enhancement #33's implicit stage-based policies. |

### Tier 2: After Data Accumulates (Sessions 34-7 through 34-11)

| Session | What | Prerequisite |
|---------|------|-------------|
| **34-7** | Tensor CP decomposition of bilateral edges | HSIC results (Session 34-2) |
| **34-8** | FastRP baseline + conditional HGT | Graph size validation |
| **34-9** | Causal mediation analysis | 500+ completed retargeting sequences |
| **34-10** | Prospect Theory value function | DDM timing data accumulated |
| **34-11** | Information Bottleneck compression | CCA results (Session 34-2) |

### Tier 3: Architectural (Sessions 34-12 through 34-14)

| Session | What | Prerequisite |
|---------|------|-------------|
| **34-12** | Contrastive Two-Tower learning | 10K+ bilateral edges per category |
| **34-13** | POMDP formalization + Offline RL | 500+ complete sequences + transition model |
| **34-14** | IDS (if mechanisms are differentially informative) | Neural-LinUCB results |

### Explicitly Skipped

| Proposed | Why Skipped |
|----------|------------|
| Meta-Thompson for Cold Start | Enhancement #33 hierarchical priors already solve this |
| CV-TMLE | No existing causal inference to improve; BCF has same prerequisite |
| Optimal Transport | Engineering investment not justified vs. HSIC + tensor |
| Active Inference | No published advertising applications; high risk |
| BOED | Premature; requires substantial offline infrastructure |

---

## SUMMARY: SPEC vs. REALITY

| Category | Spec's Assumption | Reality | Impact on Plan |
|----------|-------------------|---------|---------------|
| **1. Bandits** | "Context-free Thompson" | 3 Thompson systems, retargeting one IS contextual (barrier × archetype) | Neural-LinUCB still valuable but scope narrower |
| **2. Causal** | "Upgrade CausalForestDML" | **CausalForestDML doesn't exist** | Skip upgrade, BUILD from scratch after data accumulates |
| **3. Edge Math** | "Point-biserial correlations" | **No correlations. Hand-coded formulas.** | HSIC answers "are formulas missing non-linear structure?" |
| **4. Graph** | "Static Cypher queries" | 3 GDS algorithms ACTIVE at inference | FastRP baseline before GNN investment |
| **5. Sequential** | "Heuristic rules" | **Bayesian Thompson with hierarchical priors** | POMDP deferred; Options Framework is the right next step |
| **6. Annotations** | "No calibration" | Confidence stored but not validated | Self-consistency is the right first step |
| **7. Cognitive** | "No timing data" | Session timing exists, per-impression timing does NOT | Add timing capture to webhook first |
| **8. Info Theory** | "No dimensionality analysis" | Correct — none exists | CCA is cheap and highly informative |

**Bottom line:** The spec made 3 significant factual errors (no CausalForestDML, no point-biserial, not heuristic rules) and underestimated Enhancement #33's contribution. The recommended plan accounts for reality: build what strengthens the actual system, skip what replaces phantom implementations, defer what needs data that doesn't exist yet.
