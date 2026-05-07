# Cold Start Archetype Profiles & Scale Convention Audit

**Slice ID:** A.2.0
**Session:** 2026-05-07 (continuation; A.0 → A.1.0 → A.1 → A.2.0 → A.2)
**Predecessor:** `8a7ef23` (A.1 consolidation refactor); `c237e4b` (A.1.0 audit); `cf41115` (A.0 docs)
**Audit type:** Read-only inspection (S2 retargeting / A.1.0 maximizer-fragmentation precedent)
**Branch:** `feature/hmt-dashboard`

---

## §1 Executive Summary

**Scale convention: NORMALIZED_0_TO_1** (confirmed by Pydantic validator constraint `Field(ge=0.0, le=1.0)` on `GaussianDistribution.mean`, not just empirical clustering).

**Profile anchoring: POPULATION-ANCHORED IN INTENT, with an internal-engine population convention that systematically differs from literature norms.** Module docstring cites Costa & McCrae + Hirsh et al. 2012 (population-anchored references). Per-archetype profiles show strong differentiation (e.g., NURTURER A=0.90 vs engine-population A-avg 0.619, ACHIEVER N=0.30 vs avg 0.431) consistent with population-anchored intent. **However:** the engine's per-trait empirical mean (across 8 archetypes) systematically falls 0.04–0.11 BELOW Chris's literature-rescaled reference (e.g., engine C-avg 0.631 vs literature 0.74 rescaled). The engine appears to use a 0.5-centered population convention rather than empirical Costa-McCrae norms.

**Schema reality the audit surfaces for A.2:**
- 8 archetypes × 5 Big Five traits, all `GaussianDistribution(mean ∈ [0,1], variance ∈ {0.02, 0.03})` — variance, not std (A.2 must `sqrt` for σ)
- `mean` Pydantic-validated to [0, 1] — A.2's z-score normalization input domain locked
- All 8 archetypes have all 5 Big Five dimensions present (no missing values)
- Trait names match standard Big Five (no NEO-PI-R facet-level surprises)

**QUESTION-and-stop concerns for A.2:** **two** (see §7) — (Q11.A) which population (μ, σ) reference to use for z-score derivation: literature-rescaled vs engine-empirical vs 0.5-centered hybrid; (Q11.B) Schwartz et al. 2002 trait-correlate sign + magnitude mapping for combining 5 z-scores into a single maximizer_tendency Beta prior.

**Recommended A.2 derivation anchor (subject to Claude Proper adjudication):** use **engine-empirical population** (per-trait mean of the 8 archetypes as μ; engine's typical archetype variance as σ proxy). Rationale: keeps z-scores internally consistent with the engine's own population convention; archetype A's z-score for trait T then expresses A's deviation from "the engine's typical archetype" rather than from "literature-grade general population." This avoids the 0.04–0.11 systematic offset and produces archetype-relative-within-engine z-scores that are interpretable without literature renormalization.

---

## §2 Pass 1 — `definitions.py` schema

**File:** `adam/cold_start/archetypes/definitions.py`
**Size:** 384 lines, 1,203 words
**Top-level pattern:** module-level dict literals + a `build_archetype_definitions()` factory + `get_archetype()` / `get_all_archetypes()` accessors.

### §2.1 Module header / academic grounding

```
"""
Research-grounded psychological archetype definitions.

8 archetypes based on:
- Jung's psychological types
- Big Five personality research (Costa & McCrae)
- Advertising response studies (Matz et al., 2017)
- Trait-message matching research (Hirsh et al., 2012)

Each archetype has:
- Big Five trait profile (mean + variance)
- Regulatory focus (promotion vs prevention)
- Mechanism effectiveness priors
- Message frame preferences
"""
```

Citations point to **population-anchored** literature (Costa & McCrae = NEO-PI-R population norms; Matz et al. 2017 = trait-message matching empirical study; Hirsh et al. 2012 = trait-targeted persuasion research).

### §2.2 Imports

```python
from adam.cold_start.models.enums import (
    ArchetypeID, CognitiveMechanism, PersonalityTrait
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution
)
from adam.cold_start.models.archetypes import (
    ArchetypeTraitProfile, ArchetypeMechanismProfile, ArchetypeDefinition
)
```

### §2.3 Type definitions

#### §2.3.1 `GaussianDistribution` (`adam/cold_start/models/priors.py:135–180`)

```python
class GaussianDistribution(BaseModel):
    """Gaussian distribution for continuous traits like personality.
    Used for Big Five traits and extended constructs."""
    mean: float = Field(ge=0.0, le=1.0, default=0.5, description="Mean value")
    variance: float = Field(ge=0.0, default=0.04, description="Variance")

    @computed_field
    @property
    def std(self) -> float:
        return float(np.sqrt(self.variance))

    # ... .confidence (inverse of variance), .sample() (clipped to [0,1]),
    # .update(observation, observation_variance) (conjugate normal-normal) ...
```

**Key properties for A.2:**
- `mean` field has Pydantic validator `Field(ge=0.0, le=1.0)` — **scale convention NORMALIZED_0_TO_1 enforced at type level**, not merely empirical pattern.
- Uses `variance` not `std` — A.2 must compute `σ = sqrt(variance)` explicitly.
- `std` is a `@computed_field` (read-only), so A.2 can use `.std` to access σ without re-computing.
- `.sample()` clips to [0, 1] — confirms intent that values stay in unit interval.

#### §2.3.2 `ArchetypeTraitProfile` (`adam/cold_start/models/archetypes.py:32–63`)

```python
class ArchetypeTraitProfile(BaseModel):
    """Big Five trait profile for an archetype.
    Based on research literature for personality-behavior correlations.
    Each trait is a Gaussian with mean and variance."""
    openness: GaussianDistribution
    conscientiousness: GaussianDistribution
    extraversion: GaussianDistribution
    agreeableness: GaussianDistribution
    neuroticism: GaussianDistribution

    def to_dict(self) -> Dict[PersonalityTrait, GaussianDistribution]:
        return {
            PersonalityTrait.OPENNESS: self.openness,
            PersonalityTrait.CONSCIENTIOUSNESS: self.conscientiousness,
            PersonalityTrait.EXTRAVERSION: self.extraversion,
            PersonalityTrait.AGREEABLENESS: self.agreeableness,
            PersonalityTrait.NEUROTICISM: self.neuroticism,
        }

    def similarity_to(self, trait_values: Dict[PersonalityTrait, float]) -> float:
        """Mahalanobis-like distance normalized to [0, 1]."""
        # ...
```

**Key facts:**
- Standard Big Five 5-factor model (no NEO-PI-R facet-level decomposition; no surprises).
- Each trait is `GaussianDistribution` (not bare float; A.2 has access to per-trait variance for σ).
- Naming exactly matches Big Five canonical: `openness`, `conscientiousness`, `extraversion`, `agreeableness`, `neuroticism`.
- `to_dict()` produces `{PersonalityTrait: GaussianDistribution}` — A.2 can iterate this.

### §2.4 Archetype-construction surface pattern

`ARCHETYPE_TRAIT_PROFILES: Dict[ArchetypeID, ArchetypeTraitProfile]` is a **module-level dict literal** (no factory function, no runtime computation). Each entry constructs `ArchetypeTraitProfile(...)` with 5 `GaussianDistribution(mean=X, variance=Y)` literals.

This pattern means:
- A.2 can read the profiles directly via `from adam.cold_start.archetypes.definitions import ARCHETYPE_TRAIT_PROFILES` (or via `get_all_archetypes()` for the full `ArchetypeDefinition` records).
- Profile values are static (no environment-dependent overrides).
- A.2's tests can iterate `ArchetypeID` and assert per-archetype derived priors against expected values.

---

## §3 Pass 2 — Archetype profile extraction

All 8 archetypes have all 5 Big Five dimensions present. All variances are `0.02` or `0.03` (i.e., σ ∈ {0.1414, 0.1732}).

| Archetype | O (μ, var) | C (μ, var) | E (μ, var) | A (μ, var) | N (μ, var) |
|---|---|---|---|---|---|
| **EXPLORER** | (0.80, 0.02) | (0.45, 0.03) | (0.65, 0.03) | (0.55, 0.03) | (0.35, 0.03) |
| **ACHIEVER** | (0.55, 0.03) | (0.85, 0.02) | (0.60, 0.03) | (0.50, 0.03) | (0.30, 0.03) |
| **CONNECTOR** | (0.60, 0.03) | (0.55, 0.03) | (0.85, 0.02) | (0.80, 0.02) | (0.35, 0.03) |
| **GUARDIAN** | (0.40, 0.03) | (0.75, 0.02) | (0.40, 0.03) | (0.60, 0.03) | (0.65, 0.03) |
| **ANALYST** | (0.70, 0.02) | (0.80, 0.02) | (0.35, 0.03) | (0.50, 0.03) | (0.40, 0.03) |
| **CREATOR** | (0.90, 0.02) | (0.40, 0.03) | (0.55, 0.03) | (0.55, 0.03) | (0.50, 0.03) |
| **NURTURER** | (0.55, 0.03) | (0.65, 0.03) | (0.55, 0.03) | (0.90, 0.02) | (0.45, 0.03) |
| **PRAGMATIST** | (0.50, 0.03) | (0.60, 0.03) | (0.50, 0.03) | (0.55, 0.03) | (0.45, 0.03) |

**Notes:**
- No missing dimensions; every (archetype, trait) cell is populated.
- Variance pattern: `0.02` (σ=0.1414) used for the archetype's defining/strongest traits; `0.03` (σ=0.1732) used for non-defining traits. Lower variance = higher confidence the archetype's typical member is at that mean. This matches population-anchored intent (high-confidence claims about defining traits, lower confidence elsewhere).
- No archetype has variance >0.03 or <0.02 — variance discipline is binary.

---

## §4 Pass 3 — Scale convention detection

### §4.1 Empirical range stats (across 40 archetype-trait means)

- `min(all_means)` = **0.30** (ACHIEVER neuroticism)
- `max(all_means)` = **0.90** (CREATOR openness, NURTURER agreeableness)
- `mean(all_means)` = **0.5725** (≈ midpoint with slight upward drift from N's lower clustering)

### §4.2 Per-trait mean / range / per-trait min/max archetype

| Trait | Engine per-trait mean (across 8 archetypes) | min — archetype | max — archetype | Range |
|---|---:|---|---|---:|
| **Openness** | **0.6250** | 0.40 — GUARDIAN | 0.90 — CREATOR | 0.50 |
| **Conscientiousness** | **0.6313** | 0.40 — CREATOR | 0.85 — ACHIEVER | 0.45 |
| **Extraversion** | **0.5563** | 0.35 — ANALYST | 0.85 — CONNECTOR | 0.50 |
| **Agreeableness** | **0.6188** | 0.50 — ACHIEVER, ANALYST | 0.90 — NURTURER | 0.40 |
| **Neuroticism** | **0.4313** | 0.30 — ACHIEVER | 0.65 — GUARDIAN | 0.35 |

### §4.3 Comparison vs Chris's reference population (1–5 Likert, rescaled to 0–1)

| Trait | Chris reference (1–5) | Rescaled (0–1) | Engine empirical avg | Δ (engine − population) |
|---|---:|---:|---:|---:|
| O | 3.3 (σ ≈ 0.7) | 0.66 (σ ≈ 0.14) | 0.6250 | **−0.035** |
| C | 3.7 (σ ≈ 0.7) | **0.74** (σ ≈ 0.14) | 0.6313 | **−0.108** ⚠️ |
| E | 3.3 (σ ≈ 0.8) | 0.66 (σ ≈ 0.16) | 0.5563 | **−0.104** ⚠️ |
| A | 3.5 (σ ≈ 0.7) | **0.70** (σ ≈ 0.14) | 0.6188 | **−0.081** ⚠️ |
| N | 2.65 (σ ≈ 0.85) | **0.53** (σ ≈ 0.17) | 0.4313 | **−0.099** ⚠️ |

**Engine systematically averages 0.04–0.11 BELOW the literature-rescaled population norm across ALL FIVE traits.**

### §4.4 Scale convention classification

**Verdict: NORMALIZED_0_TO_1.**

Evidence:
- **Validator-enforced (strongest signal):** `GaussianDistribution.mean` has `Field(ge=0.0, le=1.0)` — the type system *guarantees* values stay in [0, 1].
- **Empirical:** all 40 means in [0.30, 0.90] ⊂ [0, 1]. ✅
- **Per-trait clustering qualitatively population-skew-consistent:** C-avg 0.6313 and A-avg 0.6188 cluster higher than N-avg 0.4313, matching the literature-known direction (C and A means above midpoint; N below).
- **Quantitative discrepancy** (§4.3): the engine's per-trait means systematically fall 0.04–0.11 BELOW the literature-rescaled norms. This means the engine's "population reference" is not literature-grade Costa-McCrae norms; it appears to be a **0.5-centered convention with archetype-relative deviations**.

This subtlety **matters for A.2 derivation**: see §6 + §7 (Q11.A).

---

## §5 Pass 4 — Population-anchored vs archetype-relative

### §5.1 Evidence supporting POPULATION-ANCHORED intent

- **Module docstring** explicitly cites:
  - Costa & McCrae (NEO-PI-R, the canonical Big Five population norms)
  - Hirsh et al. 2012 (trait-message matching, which presupposes population-anchored trait scores)
  - Matz et al. 2017 (advertising response studies — population-level statistics)
- **Strong per-archetype differentiation**: NURTURER A=0.90 is well above engine-population avg 0.6188 (Δ=+0.28); ACHIEVER N=0.30 is well below avg 0.4313 (Δ=−0.13). Population-anchored intent makes these defining-trait elevations meaningful.
- **Variance discipline**: defining traits get tighter variance (0.02) — high-confidence statements about how this archetype compares to population on its core trait.
- **Per-archetype `description` + `research_basis` fields** (in `archetype_metadata` dict, lines 213–322) explicitly link archetype trait elevations to population-level effect sizes (e.g., "Achievement messaging increases CTR by 18% for high-C users", "Social proof increases conversion 34% for Connectors"). These claims only make sense if "high-C" and "Connectors" are population-anchored categories.

### §5.2 Evidence supporting ARCHETYPE-RELATIVE convention

- **Quantitative offset from literature** (§4.3): if profiles were literature-anchored, engine averages should match literature-rescaled means within sampling error (~±0.02). The systematic 0.04–0.11 below-literature offset suggests the engine's reference population is internal, not literature-grade.
- **Per-trait engine variance ≈ 0.14–0.17** matches literature-rescaled σ closely — so engine variance IS population-grade, but engine mean is population-grade-shifted-down.
- **Engine archetype means cluster around 0.5–0.65** (range 0.30–0.90 with most values 0.40–0.80), not around literature norms (0.53–0.74). This suggests the engine may be using `0.5` as the population-midpoint anchor, with archetype profiles expressed as deviations from 0.5 (rather than from literature norm).

### §5.3 Synthesis verdict

**The engine's archetype profiles are POPULATION-ANCHORED IN INTENT, with an INTERNAL POPULATION CONVENTION that systematically differs from literature.** Specifically:
- Direction of differentiation matches literature (C/A elevated, N suppressed across most archetypes).
- Defining-trait elevations are meaningful "above population" claims (NURTURER A is way above the engine's typical archetype A).
- BUT the absolute scale uses a different reference: the engine appears to use `0.5` as the implicit population midpoint, with archetype values expressed as deviations from 0.5 (constrained to [0, 1] by the validator), rather than against literature-rescaled norms.

**For A.2's z-score derivation**, this means:
- Using **literature-rescaled (μ, σ)** as reference (Chris's option α) would systematically produce negative z-scores for most engine archetypes on most traits — because the engine's average archetype falls below literature norms by construction. The math would correctly express "the engine's archetypes are conservatively-calibrated below literature population," but the maximizer_tendency Beta priors derived from those z-scores would all skew low.
- Using **engine empirical (μ, σ)** as reference (option β) produces z-scores expressing each archetype's deviation from "the engine's typical archetype" — internally consistent with the engine's convention. The maximizer_tendency Beta priors derived from these z-scores would differentiate archetypes against the engine's own population, which is what the engine itself does for everything else.
- Using **0.5-centered with engine empirical σ** (option γ) is a hybrid: anchor at the engine's apparent midpoint convention, but use real engine variance for the spread. This is the simplest interpretation and likely closest to how the profiles were authored.

**Audit recommendation for §6:** option β (engine empirical) is the safest default. Option γ (0.5-centered) is the closest match to the engine's apparent author-intent. Both avoid option α's systematic downward bias.

---

## §6 Recommended A.2 Derivation Anchor

### §6.1 Population (μ, σ) values for z-score normalization

**Audit recommendation:** use **engine empirical per-trait stats** (option β). Computed from §4.2:

| Trait | μ (engine empirical) | σ (engine empirical sample std) |
|---|---:|---:|
| Openness | 0.6250 | 0.1604 |
| Conscientiousness | 0.6313 | 0.1607 |
| Extraversion | 0.5563 | 0.1675 |
| Agreeableness | 0.6188 | 0.1416 |
| Neuroticism | 0.4313 | 0.1130 |

(σ = sample std of the 8 archetype means per trait, *not* the within-archetype variance from `GaussianDistribution`.)

### §6.2 Why engine empirical (option β) over Chris's literature reference (option α)

- **Internal consistency:** A.2's outputs (Beta priors per archetype) will be consumed downstream by the same engine that produced the input profiles. Z-scoring against the engine's own convention keeps the derivation self-consistent.
- **Avoids systematic bias:** option α's literature reference would produce mostly-negative z-scores for the engine's archetypes (because engine means are 0.04–0.11 below literature). The maximizer_tendency Beta priors derived from those z-scores would skew low across all archetypes, defeating the differentiation A.2 is supposed to express.
- **Preserves directional differentiation:** option β's engine reference maps the engine's strongest-C archetype (ACHIEVER, C=0.85) to the highest C-z-score (z=(0.85−0.6313)/0.1607 ≈ +1.36), and its lowest-C archetype (CREATOR, C=0.40) to the lowest C-z-score (z≈−1.44). This is the differentiation A.2 needs.

### §6.3 Schwartz et al. 2002 trait-correlate sign mapping (audit-recommended starting point — Q11.B for Claude Proper)

Per Schwartz et al. 2002 + subsequent literature (Iyengar et al. 2006, Diab et al. 2008, Misuraca et al. 2015), the maximizer trait correlates with Big Five as follows:

| Big Five trait | Direction of correlation with maximizer_tendency | Strength |
|---|---|---|
| **Openness** | + (positive) | weak-to-moderate |
| **Conscientiousness** | + (positive) | moderate (deliberation, thoroughness) |
| **Extraversion** | ± (mixed in literature) | weak |
| **Agreeableness** | − (negative; satisficers more agreeable) | weak |
| **Neuroticism** | + (positive; maximizers experience more regret/anxiety) | moderate (Schwartz's central finding: maximizers report more depression, regret, less life satisfaction) |

**Audit's suggested A.2 derivation formula** (subject to Q11.B Claude Proper adjudication):

```
maximizer_z = (
    +0.20 * z(O) +
    +0.40 * z(C) +
    +0.05 * z(E) +
    -0.15 * z(A) +
    +0.40 * z(N)
)
```

Weights derived from approximate Schwartz literature effect sizes (C and N are the strongest correlates; O moderate-positive; A weakly-negative; E near-zero). Sum of |weights| ≈ 1.20 — Claude Proper may want to normalize to sum-to-1 for cleaner interpretability.

Conversion of `maximizer_z` to Beta(α, β) prior:
- Map z-score to mean μ_max ∈ (0, 1) via logistic: `μ_max = 1 / (1 + exp(-maximizer_z))`
- Choose total pseudo-count `n` (audit suggestion: `n = 10` for soft prior, `n = 20` for stronger archetype anchoring)
- Then `α = μ_max * n`, `β = (1 - μ_max) * n`

### §6.4 Predicted Beta priors per archetype (audit-recommended starting point)

Using §6.1 (engine empirical reference) + §6.3 (Schwartz weights) + n=10 pseudo-count:

| Archetype | maximizer_z | μ_max (logistic) | α (n=10) | β (n=10) |
|---|---:|---:|---:|---:|
| EXPLORER | +0.20·z(0.80;O) + 0.40·z(0.45;C) + 0.05·z(0.65;E) − 0.15·z(0.55;A) + 0.40·z(0.35;N) ≈ +0.21·1.09 + 0.40·(−1.13) + 0.05·0.56 − 0.15·(−0.49) + 0.40·(−0.72) ≈ −0.42 | 0.40 | 4.0 | 6.0 |
| ACHIEVER | ≈ −0.43·0 + 0.40·1.36 + 0.05·0.26 − 0.15·(−0.84) + 0.40·(−1.16) ≈ +0.23 | 0.56 | 5.6 | 4.4 |
| CONNECTOR | ≈ +0.20·(−0.16) + 0.40·(−0.51) + 0.05·1.75 − 0.15·1.28 + 0.40·(−0.72) ≈ −0.65 | 0.34 | 3.4 | 6.6 |
| GUARDIAN | ≈ +0.20·(−1.40) + 0.40·0.93 + 0.05·(−0.93) − 0.15·(−0.13) + 0.40·2.02 ≈ +0.85 | 0.70 | 7.0 | 3.0 |
| ANALYST | ≈ +0.20·0.47 + 0.40·1.05 + 0.05·(−1.23) − 0.15·(−0.84) + 0.40·(−0.28) ≈ +0.45 | 0.61 | 6.1 | 3.9 |
| CREATOR | ≈ +0.20·1.71 + 0.40·(−1.44) + 0.05·(−0.04) − 0.15·(−0.49) + 0.40·0.61 ≈ +0.06 | 0.51 | 5.1 | 4.9 |
| NURTURER | ≈ +0.20·(−0.45) + 0.40·0.12 + 0.05·(−0.04) − 0.15·1.99 + 0.40·0.16 ≈ −0.27 | 0.43 | 4.3 | 5.7 |
| PRAGMATIST | ≈ +0.20·(−0.78) + 0.40·(−0.20) + 0.05·(−0.34) − 0.15·(−0.49) + 0.40·0.16 ≈ −0.16 | 0.46 | 4.6 | 5.4 |

(Numerical computations are illustrative — A.2 will compute these in code with precise floating-point values.)

**Pattern check:** GUARDIAN gets highest maximizer prior (high N + high C + low O) → matches Schwartz finding that maximizers are anxious/conscientious. EXPLORER + CONNECTOR get lowest maximizer priors → matches "satisficers are exploratory and socially-bonded" intuition. ANALYST also high (high C, deliberate) — matches. ACHIEVER moderate-high (high C, low N partially offsets). The differentiation pattern is plausible.

### §6.5 Implementation notes for A.2

- A.2 should **import** `ARCHETYPE_TRAIT_PROFILES` and `PersonalityTrait` from `adam.cold_start` rather than re-deriving values; this anchors A.2 to the canonical engine source.
- A.2 should use `GaussianDistribution.mean` and `.std` (computed_field via `sqrt(variance)`) — never `.variance` directly in z-score math.
- Derivation should be a **pure function** (`derive_maximizer_beta_priors(profiles) -> Dict[ArchetypeID, BetaDistribution]`) so A.2's tests can pin invariants on the math without engine-state coupling.
- A.2's tests should pin: (i) every archetype produces α > 0, β > 0; (ii) μ_max for each archetype matches the §6.4 table within tolerance 1e-3; (iii) the overall pattern (GUARDIAN/ANALYST high, EXPLORER/CONNECTOR low) holds.

---

## §7 QUESTION-and-stop concerns surfaced

### Q11.A — Reference population for z-score derivation

**Three options surface from the audit; choose:**

(α) **Literature-rescaled population norms** (from Chris's reference, rescaled to [0, 1]):
- O: μ=0.66, σ=0.14
- C: μ=0.74, σ=0.14
- E: μ=0.66, σ=0.16
- A: μ=0.70, σ=0.14
- N: μ=0.53, σ=0.17

This anchors derivation to literature-grade Costa-McCrae norms but produces systematically-low z-scores for the engine's archetypes (because engine means are 0.04–0.11 below literature).

(β) **Engine empirical population** (per-trait sample mean + std of the 8 archetypes — audit recommendation):
- O: μ=0.6250, σ=0.1604
- C: μ=0.6313, σ=0.1607
- E: μ=0.5563, σ=0.1675
- A: μ=0.6188, σ=0.1416
- N: μ=0.4313, σ=0.1130

Internally consistent with the engine's convention; preserves archetype differentiation; what the audit recommends.

(γ) **0.5-centered hybrid** (μ=0.5 for all traits, σ from engine empirical):
- All traits: μ=0.5, σ as in option β

Closest match to the engine's apparent author-intent (0.5-centered convention).

**Recommendation: option β.** Decision needed from Claude Proper.

### Q11.B — Schwartz trait-correlate weights

The audit's §6.3 suggested formula uses approximate weights from literature (`+0.20·O + 0.40·C + 0.05·E − 0.15·A + 0.40·N`). These are illustrative; Claude Proper should confirm:
- Which Schwartz/follow-up paper to anchor weights against (Schwartz 2002 alone, vs Iyengar 2006, vs Misuraca 2015 meta-analysis)?
- Whether to normalize weights to sum-to-1 for interpretability
- Whether to use simple linear z-score combination, or a more sophisticated approach (e.g., logistic regression coefficients from Schwartz's published model)

### Q11.C (minor) — Pseudo-count `n` for Beta prior strength

The audit's §6.4 used `n=10` (soft prior). Higher `n` (e.g., 20 or 40) would strengthen the archetype anchoring but reduce flexibility for per-user posterior updates. Decision needed.

---

## §8 Audit closure

**Audit complete.** Memo committed for A.2 reference. Slice A.2.0 ships read-only. No code modifications.

**State at standdown:**
- Memo at `docs/audits/COLD_START_ARCHETYPE_PROFILES_AUDIT.md` (this file).
- Branch `feature/hmt-dashboard` HEAD unchanged: `8a7ef23` (A.1).
- Working tree: this new file + the ongoing `docs/MEMORY.md` EVE update + `docs/PLATFORM_INVENTORY_2026_05_07.md` (untracked from earlier).

**Next session (A.2):** Claude Proper adjudicates Q11.A–C. A.2 prompt issued with locked decisions on (i) reference population (μ, σ), (ii) Schwartz trait-correlate weight formula, (iii) Beta-prior pseudo-count strength. Claude Code executes the derivation per §6.5 + adjudicated parameters with tests pinning per-archetype Beta priors.

---

**End of audit.**
