# Enhancement #34: Unified Priority Assessment
## Original 5 Tier 1 Sessions + Addendum B ("Physics of Conversion")
## Date: March 26, 2026

---

## The Question

We have 5 confirmed Tier 1 sessions from the main Enhancement #34 assessment, plus 5 proposed categories from Addendum B. How do they rank together? What should we build, in what order?

---

## ADDENDUM B ASSESSMENT: CATEGORY BY CATEGORY

### B.1: Phase Transition / Critical Slowing Down

**What it proposes:** Conversion is a sudden phase transition, not gradual. Detect approaching conversion via increasing variance and autocorrelation in behavioral signals (critical slowing down). Universal across archetypes — requires no psychological annotation.

**Assessment against codebase:**
- Per-event timestamps: AVAILABLE (BehavioralSignal.timestamp)
- Rolling variance computation: ProcessedSignalSet already computes engagement_velocity on 3-signal windows
- Data adequacy: CONDITIONAL — need ≥5 timestamped events per user. LUXY Ride has 1,492 edges but per-user event depth is unverified.

**Honest evaluation:** The CONCEPT is powerful — a universal detection signal from pure behavioral telemetry. But the TEST requires per-user behavioral time series with sufficient depth, and we don't know if our retargeting data has that yet. The test itself is cheap (rolling variance computation) but the data prerequisite is uncertain.

**Verdict: HIGH POTENTIAL, but test feasibility first.** If we already have ≥5 events per user from existing webhook data or session tracking, this test costs hours. If not, we need to accumulate data from Enhancement #33's live sequences first.

**Priority adjustment:** Bundle with the DDM timing capture session (34-5). Both need the same data (timestamped behavioral sequences), and DDM timing capture CREATES the data that critical slowing down CONSUMES.

---

### B.2: Conversion Energy Landscape / Frustration Analysis

**What it proposes:** Bilateral alignment dimensions define an energy landscape. Negatively correlated dimension pairs among converters are "frustrated" — satisfying one makes the other worse. Frustration predicts which prospects will get stuck (kinetic traps).

**Assessment against codebase:**
- 27-dimension alignment vectors: AVAILABLE per edge in luxury_bilateral_edges.json
- Converted edges: FILTERABLE (evangelized + satisfied = 754 edges)
- Archetype stratification: MISSING from edges — needs mapping

**Honest evaluation:** This is a straightforward correlation matrix computation on data we already have. The frustration concept maps directly to Enhancement #33's barrier diagnosis — if we know which dimension pairs conflict, we know which barriers to address SEQUENTIALLY rather than simultaneously. The test costs minutes (numpy.cov on 754 × 27 matrix).

**However:** The archetype mapping gap means we can only compute global frustration, not per-archetype frustration. Global frustration is still useful but less actionable.

**Verdict: BUILD — bundled with HSIC session (34-2).** Both HSIC and frustration analysis operate on the same bilateral edge data. HSIC tests non-linear dependencies; frustration tests negative covariance. Same data, complementary insights.

---

### B.3: Stochastic Resonance / Optimal Message Variation

**What it proposes:** Adding controlled variation to retargeting messages can IMPROVE conversion if calibrated to the inverted-U optimum. Too little variation = mere exposure wears out. Too much = coherence breaks. Optimal variation cooperates with buyer's internal oscillation.

**Assessment against codebase:**
- A/B testing framework: EXISTS (adam/experimentation/service.py)
- Creative variation: CONFIGURABLE at mechanism/construal/scaffold level
- Continuous noise parameter: DOES NOT EXIST

**Honest evaluation:** The theory is elegant and connects to DDM (stochastic resonance enhances drift rate). But it requires an A/B test to validate — we can't test it computationally on existing data. The A/B test requires live traffic, which means the LUXY Ride pilot must be running first.

**Verdict: DEFER — requires live A/B test data.** Interesting theory, but premature to build until Enhancement #33 is deployed and generating live retargeting sequences. Note the concept in the retargeting system design so the variation_level parameter is ready when we want to test it.

---

### B.4: Temporal Burstiness

**What it proposes:** Human behavior follows power-law inter-event times (bursts of activity + long quiescence), not Poisson. Retargeting touches should synchronize with bursts — deliver during active periods, suppress during quiescence.

**Assessment against codebase:**
- Timestamped event sequences: AVAILABLE (same as Phase Transition test)
- Inter-event timing: COMPUTABLE from ProcessedSignalSet.raw_signals
- Current timing model: Fixed intervals in SuppressionController (min_hours_between_touches = 12)

**Honest evaluation:** The burstiness parameter B is cheap to compute (variance and mean of inter-event times). If B >> 0, the fixed-interval timing model is provably suboptimal. The tactical implication is powerful — replace fixed intervals with burst-aware delivery — and directly improves Enhancement #33's SuppressionController.

**BUT:** Same data prerequisite as Phase Transition — need sufficient per-user timestamped events.

**Verdict: BUNDLE with DDM timing session (34-5).** Same data, same prerequisite. If we capture timing data, both burstiness and critical slowing down become testable. The burst-aware timing controller is a direct upgrade to the SuppressionController we just built.

---

### B.5: Unified Conversion Landscape

**What it proposes:** All four Addendum B concepts are aspects of one framework: alignment space = energy landscape, conversion = phase transition, stalled = kinetic trap, variation = stochastic resonance, timing = burstiness. The unified test: is conversion probability vs. composite alignment SIGMOIDAL?

**Assessment against codebase:**
- Composite alignment scores: AVAILABLE per edge
- Conversion outcomes: AVAILABLE (binary from edge outcome field)
- Sigmoid fit: scipy.optimize, no existing code

**Honest evaluation:** This is the CHEAPEST and MOST DECISIVE test in the entire Addendum B. Fit a logistic curve to 1,492 (composite_alignment, converted_binary) pairs. If the curve is sigmoidal with Hill coefficient nH >> 1, the energy landscape framework is validated. If linear, it's not.

This test costs MINUTES and determines whether the rest of Addendum B is worth building.

**Verdict: BUILD FIRST — before anything else in Addendum B.** This is the gate test. Run it in Session 34-2 alongside HSIC.

---

## UNIFIED PRIORITY RANKING

Combining all 10 candidates (5 original + 5 Addendum B):

| Rank | Session | What | Source | Why This Order | Est. Time |
|------|---------|------|--------|----------------|-----------|
| **1** | **34-2** | **HSIC + CCA + Sigmoid/Hill + Frustration** | Main #34 + Addendum B | These are all DIAGNOSTIC TESTS on existing data. They determine what else to build. Sigmoid/Hill test validates the entire Addendum B framework. HSIC validates whether hand-coded formulas miss non-linear structure. CCA reveals effective dimensionality. Frustration identifies conflicting dimension pairs. Same data source, same session. | 1-2 days |
| **2** | **34-3** | **Neural-LinUCB with 43-dim bilateral context** | Main #34 | Biggest mechanism selection improvement. Uses context that currently flows through the cascade but is ignored by Thompson Sampling. Independent of diagnostic results — always valuable. | 3-4 days |
| **3** | **34-4** | **Self-consistency N=3 + conformal prediction** | Main #34 | Cheapest annotation quality improvement. Directly strengthens every bilateral edge. No prerequisites. | 2-3 days |
| **4** | **34-5** | **DDM timing capture + burstiness analysis + critical slowing down** | Main #34 + Addendum B | Captures the timing data that enables THREE downstream concepts: DDM parameter estimation (Category 7), burstiness-aware timing (Addendum B.4), and critical slowing down detection (Addendum B.1). The capture itself is low-cost (add fields to webhook). The analysis follows when data accumulates. | 2-3 days |
| **5** | **34-6** | **Options Framework for TTM stages** | Main #34 | Low cost formalization of Enhancement #33's implicit stage policies. Can run independently. | 1-2 days |

### CONDITIONAL on Session 34-2 Results

| Condition | Then Build | Skip |
|-----------|-----------|------|
| Sigmoid/Hill test: nH >> 1 (conversion IS a phase transition) | Critical slowing down detector, energy landscape scoring, frustration-aware retargeting sequencing | If nH ≈ 1 (linear), skip all Addendum B physics frameworks |
| HSIC: >20% additional non-linear dependencies found | Update bilateral edge formulas with non-linear terms | If <5%, current formulas are sufficient |
| CCA: <20 effective dimensions | Information Bottleneck compression (Tier 2) | If >40, dimensions are mostly information-bearing |
| Frustration: strong negative covariance pairs found | Frustration-aware mechanism sequencing in Enhancement #33 | If no negative pairs, landscape is smooth |

### Deferred (Tier 2+)

| Item | Why Deferred | Prerequisite |
|------|-------------|-------------|
| Stochastic resonance A/B test | Requires live retargeting traffic | LUXY Ride pilot deployed |
| Tensor CP decomposition | Depends on HSIC results | Session 34-2 |
| FastRP + HGT | Independent but lower priority | Graph size validation |
| Prospect Theory value function | Depends on DDM timing data | Session 34-5 |
| Causal mediation analysis | Needs 500+ complete sequences | Enhancement #33 learning data |

### Explicitly Skipped (with reasons)

| Item | Reason |
|------|--------|
| Meta-Thompson cold start | Enhancement #33 hierarchical priors solve this |
| CV-TMLE | No causal inference exists to improve |
| Optimal Transport | Engineering cost vs. HSIC+tensor not justified |
| Active Inference | No advertising applications, high risk |
| BOED | Premature, needs substantial infrastructure |

---

## THE SESSION 34-2 MEGA-SESSION

Session 34-2 is now the critical gate. Four diagnostic tests on existing data:

```
INPUT: 1,492 LUXY Ride bilateral edges (27 dims + outcome)

TEST 1: Sigmoid/Hill Coefficient
  → P(conversion) vs composite_alignment
  → Fit logistic: nH >> 1 = phase transition confirmed
  → TIME: 30 minutes

TEST 2: HSIC vs Point-Biserial
  → All 65×65 buyer-seller dimension pairs
  → Count additional non-linear dependencies
  → TIME: 1-2 hours

TEST 3: CCA Dimensionality
  → 65 buyer dims × conversion outcome
  → 65 seller dims × conversion outcome
  → Number of significant canonical variates
  → TIME: 30 minutes

TEST 4: Frustration Covariance
  → 27×27 covariance matrix for converted edges (n=754)
  → Identify negatively correlated dimension pairs
  → Anti-correlate total frustration with conversion rate
  → TIME: 30 minutes

TOTAL: Half a day of analysis that determines the direction
       of the next 30+ person-weeks of implementation.
```

---

## ADDENDUM B IMPACT ASSESSMENT SUMMARY

| Category | Validated? | Impact if True | Cost to Test | Build Priority |
|----------|-----------|---------------|-------------|----------------|
| Phase Transition | UNKNOWN (need sigmoid test) | VERY HIGH — universal detection signal | MINUTES (sigmoid fit) | Test in 34-2, build in 34-5 if confirmed |
| Frustration Analysis | UNKNOWN (need covariance) | HIGH — directly improves retargeting sequencing | MINUTES (numpy.cov) | Test in 34-2, build immediately if confirmed |
| Burstiness | UNKNOWN (need timestamped data depth) | MEDIUM-HIGH — improves touch timing | HOURS (if data exists) | Test in 34-5 with timing capture |
| Stochastic Resonance | UNTESTABLE (needs live A/B) | MEDIUM — principled variation tuning | WEEKS (A/B test) | Defer until LUXY Ride pilot live |
| Unified Landscape | Depends on Tests 1-4 | VERY HIGH if all tests pass | Synthesis of above | Conditional on 34-2 results |

**Bottom line:** Addendum B is intellectually compelling and the spec is admirably honest about testability. The physics MIGHT apply — and the tests to find out cost hours, not weeks. The sigmoid test in Session 34-2 is the lynchpin: if conversion IS a phase transition, the entire framework follows with the force of physics. If it's not, we document that and move on. The spec itself says exactly this.
