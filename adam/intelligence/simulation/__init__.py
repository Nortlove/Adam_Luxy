# =============================================================================
# Phase 9 — Pre-Launch Validation Simulation Framework
# Location: adam/intelligence/simulation/
# =============================================================================
"""Per directive Phase 9 + Appendix A: full-factorial / LHS-sampled
simulation across realistic LUXY-scale parameters; comparison of
architectures (A: marginal additive baseline → B: trilateral cascade →
C: trilateral + interaction → D: full proposed stack → E: D + counter-
factual logging); metrics at multiple horizons.

THE SIMULATION

Per Appendix A (directive lines 1148-1173):

    Variables to vary (full factorial or LHS-sampled):
      - User base CTR: {0.05%, 0.15%, 0.5%}
      - Conversion rate given click: {0.5%, 2%, 5%}
      - True trait × state × context interaction strength:
            {none, weak, moderate, strong}
      - Cohort separation: {indistinguishable, weakly separable,
            strongly separable}
      - Non-stationarity regime: {stationary, slow drift, abrupt switching}
      - Audience size per cohort: {500, 2,000, 10,000}
      - Per-user impression rate: {2/week, 7/week, 20/week}

    Architectures to compare (5):
      A: marginal additive scoring (baseline).
      B: trilateral cascade only (Spine #4).
      C: trilateral + interaction model (Spine #4 + Spine #1's δ_iac).
      D: full proposed stack (Spines #1, #2, #4, #5, #7).
      E: full stack + counterfactual logging (D + Spine #6).

    Metrics at 2-, 4-, 6-week horizons:
      - Cumulative lift over a non-cognitive baseline (vanilla LinUCB
        with demographic context).
      - Posterior-credible-interval width on per-cohort uplift.
      - Time-to-confident-best-arm per cohort (mSPRT stopping time).
      - Robustness to abrupt non-stationarity (lift recovery time
        after a regime switch).
      - Counterfactual-trace efficiency multiplier (effective sample
        size with vs. without Spine #6).

OUTPUT

    A defensible *order of marginal contribution* for each cognitive
    primitive against the priority list in Section 9, plus a
    "this is what each component is worth" story for the partner.

WRAP-OUT HANDOFF (2026-05-02): Phase 9 is the highest-priority
multi-session arc before v3 Phase 1. The hard-stop criterion is
"Phase 9 simulation has run end-to-end on at least the 5-architecture
× 2-horizon subset" — this module's __init__ is the start commit
for that arc.

MODULE STRUCTURE
"""

from adam.intelligence.simulation.architectures import (
    Architecture,
    MarginalAdditiveBaseline,
    TrilateralCascadeOnly,
)
from adam.intelligence.simulation.config import (
    SimulationConfig,
    NonStationarityRegime,
    InteractionStrength,
    CohortSeparation,
)
from adam.intelligence.simulation.population import (
    SyntheticPopulation,
    SyntheticUser,
    generate_population,
)
from adam.intelligence.simulation.runner import (
    SimulationResult,
    run_single_cell,
)
from adam.intelligence.simulation.world import (
    SyntheticWorld,
    Impression,
    Outcome,
)

__all__ = [
    # config
    "SimulationConfig",
    "NonStationarityRegime",
    "InteractionStrength",
    "CohortSeparation",
    # population
    "SyntheticPopulation",
    "SyntheticUser",
    "generate_population",
    # world
    "SyntheticWorld",
    "Impression",
    "Outcome",
    # architectures
    "Architecture",
    "MarginalAdditiveBaseline",
    "TrilateralCascadeOnly",
    # runner
    "SimulationResult",
    "run_single_cell",
]
