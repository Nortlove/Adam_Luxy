# =============================================================================
# Phase 9 simulation — runner (one cell × one architecture × one horizon)
# Location: adam/intelligence/simulation/runner.py
# =============================================================================
"""Run one (config, architecture) cell to completion; emit a
SimulationResult with the metrics named in directive Appendix A
lines 1166-1171.

v0.1 ships:
  * cumulative_lift_over_baseline — directive line 1167
  * total_impressions / total_conversions
  * per_mechanism_n / per_mechanism_conversions

Subsequent slices add the remaining metrics (CI width on per-cohort
uplift, time-to-confident-best-arm, robustness-to-non-stationarity,
counterfactual-trace efficiency).

The "non-cognitive baseline" (per directive line 1167) is the ε-
greedy MarginalAdditiveBaseline — when run with seed parity it
provides an apples-to-apples reference. For the lift metric we use
the BASELINE arm's conversion rate (the population's
``user_base_ctr × conversion_rate_given_click``) as the ground-truth
zero-skill conversion rate; lift is computed as
(architecture_conversion_rate - baseline_conversion_rate) /
baseline_conversion_rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from adam.intelligence.simulation.architectures import Architecture
from adam.intelligence.simulation.config import SimulationConfig
from adam.intelligence.simulation.population import (
    SyntheticPopulation,
    generate_population,
)
from adam.intelligence.simulation.world import (
    Outcome,
    SyntheticWorld,
)


@dataclass(frozen=True)
class SimulationResult:
    """Outcome of one run: (config × architecture × horizon).

    ``config``: the SimulationConfig executed.
    ``architecture_name``: which architecture this is for.
    ``horizon_weeks``: horizon length used.
    ``total_impressions`` / ``total_conversions``: stream totals.
    ``cumulative_conversion_rate``: total_conversions / total_impressions.
    ``cumulative_lift_over_baseline``: per directive line 1167 — lift
        relative to the population's baseline conversion rate
        (``user_base_ctr × conversion_rate_given_click``). Positive
        lift = the architecture beats the zero-skill expectation;
        negative = it under-performs.
    ``per_mechanism_n`` / ``per_mechanism_conversions``: action-space
        breakdowns for downstream analysis.
    """

    config: SimulationConfig
    architecture_name: str
    horizon_weeks: int
    total_impressions: int
    total_conversions: int
    cumulative_conversion_rate: float
    cumulative_lift_over_baseline: float
    per_mechanism_n: Dict[str, int] = field(default_factory=dict)
    per_mechanism_conversions: Dict[str, int] = field(default_factory=dict)


def run_single_cell(
    config: SimulationConfig,
    architecture: Architecture,
    *,
    population: Optional[SyntheticPopulation] = None,
) -> SimulationResult:
    """Run one (config × architecture × horizon) cell to completion.

    Args:
        config: the simulation cell.
        architecture: the architecture under test (must satisfy the
            Architecture Protocol).
        population: optional pre-built population (useful for
            cross-architecture comparison on identical population);
            when None, builds a fresh population from config.

    Returns:
        SimulationResult with cumulative + per-mechanism metrics.
    """
    if population is None:
        population = generate_population(config)

    world = SyntheticWorld(population)
    architecture.configure(population)

    impressions = world.stream_impressions()
    per_mech_n: Dict[str, int] = {}
    per_mech_conv: Dict[str, int] = {}
    total_conv = 0

    for impression in impressions:
        mech = architecture.select_mechanism(impression)
        outcome = world.deliver_outcome(impression, mech)
        architecture.record_outcome(outcome)

        per_mech_n[mech] = per_mech_n.get(mech, 0) + 1
        if outcome.converted:
            per_mech_conv[mech] = per_mech_conv.get(mech, 0) + 1
            total_conv += 1

    n_imp = len(impressions)
    cum_rate = total_conv / float(n_imp) if n_imp > 0 else 0.0

    baseline_rate = (
        config.user_base_ctr * config.conversion_rate_given_click
    )
    if baseline_rate > 0:
        lift = (cum_rate - baseline_rate) / baseline_rate
    else:
        lift = 0.0

    return SimulationResult(
        config=config,
        architecture_name=getattr(
            architecture, "name", type(architecture).__name__,
        ),
        horizon_weeks=config.horizon_weeks,
        total_impressions=n_imp,
        total_conversions=total_conv,
        cumulative_conversion_rate=cum_rate,
        cumulative_lift_over_baseline=lift,
        per_mechanism_n=per_mech_n,
        per_mechanism_conversions=per_mech_conv,
    )
