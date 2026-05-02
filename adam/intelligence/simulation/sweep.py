# =============================================================================
# Phase 9 simulation — sweep runner + metrics + artifact serialization
# Location: adam/intelligence/simulation/sweep.py
# =============================================================================
"""Multi-cell sweep runner over the directive's Appendix A grids.

Per the 2026-05-02 wrap-out hard-stop criterion (i): "Phase 9
simulation has run end-to-end on at least the 5-architecture × 2-
horizon subset". This module is the runner that produces the
artifact.

Scope:
  * 5 architectures (A/B/C/D/E from Slices 25/28/29/30/31).
  * 2 horizons (default first two of HORIZON_WEEKS_GRID = (2, 4)).
  * Within each (architecture, horizon) cell, sweep over the 7
    Appendix A grids (CTR / conversion-rate / interaction /
    cohort-separation / non-stationarity / audience / impression-
    rate). Full factorial when grid product ≤ FULL_FACTORIAL_CAP;
    LHS sampling otherwise.
  * Per-cell timeseries (sampled at decile intervals) for trajectory
    metrics (lift evolution, top-mechanism stability, CI width).
  * Serializable to JSON-lines for auditable artifact persistence.

Output requirements (per the wrap-out greenlight):

  1. SweepResult serializable to disk (JSON-lines).
  2. sweep_summary(result) returns the directive line 1166-1171
     metrics in tabular form (cumulative lift over baseline,
     posterior CI width, mSPRT stopping-time proxy, robustness-to-
     non-stationarity recovery time, counterfactual-trace ESS
     multiplier).
  3. Non-stationarity recovery sub-test: when non_stationarity =
     ABRUPT_SWITCHING, produce a per-architecture recovery-time
     curve (NOT just a lift average).

Honest discipline: this slice ships the SUBSTRATE — config-space
enumeration, runner, metric extractors, persistence. The actual
sweep EXECUTION at scale is the next step, run separately to
produce the artifact.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Appendix A lines 1148-1173 (variables /
    architectures / metrics) + 2026-05-02 wrap-out hard-stop
    criterion (i) + Slice 25/28/29/30/31 (the 5 architectures
    this sweep aggregates).

(b) Tests pin: full-factorial vs LHS routing; LHS produces
    distinct cells; per-cell determinism under matched seed;
    SweepResult JSON-lines round-trips losslessly; sweep_summary
    produces directive-named columns; non-stationarity recovery-
    time computed only on ABRUPT_SWITCHING cells; ESS multiplier
    computed only for E; per-architecture distributions correctly
    grouped.

(c) calibration_pending=True. v0.1 mSPRT stopping time is a
    proxy (time-to-first-stable-top-arm); rigorous mSPRT log-
    likelihood-ratio test is sibling slice. v0.1 posterior CI
    width uses Beta quantile via scipy.stats. A14 flag carried
    from Slice 25's PHASE_9_SIM_CALIBRATION_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Rigorous mSPRT formalism with log-likelihood-ratio crossing.
      v0.1 uses time-to-first-stable-top-arm proxy (top mechanism
      hasn't changed in last K consecutive observations).
    * Parquet serialization. v0.1 ships JSON-lines (zero new
      dependencies + diffable artifacts). Parquet for large
      sweeps is sibling.
    * Full-LUXY-scale sweep execution at audience_size=10000.
      v0.1 substrate supports it; the actual scaled run is a
      separate operational slice.
    * Aggregation into "order of marginal contribution" report
      narrative (directive line 1173). v0.1 ships the metric
      tables; the partner-facing narrative rendering is sibling.
"""

from __future__ import annotations

import itertools
import json
import logging
import math
import random
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import (
    Any, Callable, Dict, Iterable, List, Optional, Tuple,
)

from adam.intelligence.simulation.architectures import (
    Architecture,
    FullProposedStack,
    FullStackPlusCounterfactual,
    MarginalAdditiveBaseline,
    TrilateralCascadeOnly,
    TrilateralWithInteraction,
)
from adam.intelligence.simulation.config import (
    AUDIENCE_SIZE_GRID,
    CTR_GRID,
    CONVERSION_RATE_GRID,
    CohortSeparation,
    HORIZON_WEEKS_GRID,
    IMPRESSION_RATE_GRID,
    InteractionStrength,
    NonStationarityRegime,
    SimulationConfig,
)
from adam.intelligence.simulation.population import (
    SyntheticPopulation,
    generate_population,
)
from adam.intelligence.simulation.world import (
    Outcome,
    SyntheticWorld,
)

logger = logging.getLogger(__name__)


# Cap above which LHS sampling replaces full factorial.
FULL_FACTORIAL_CAP: int = 200

# Number of timeseries snapshots per cell run (decile-spaced).
TIMESERIES_SAMPLES_PER_CELL: int = 10

# How many consecutive impressions the top arm must stay constant
# to count as "stable" for the mSPRT stopping-time proxy.
STABLE_TOP_ARM_WINDOW: int = 30


# =============================================================================
# Default architecture factories — keyed by canonical name
# =============================================================================


def default_architecture_factories() -> Dict[
    str, Callable[[int], Architecture]
]:
    """Map canonical architecture name → factory(seed) -> instance.

    Matches the directive's A/B/C/D/E lineup. Each factory takes a
    seed kwarg so the sweep runner can derive per-cell determinism.
    """
    return {
        "A_marginal_additive": lambda seed: (
            MarginalAdditiveBaseline(seed=seed)
        ),
        "B_trilateral_cascade_only": lambda seed: (
            TrilateralCascadeOnly(seed=seed)
        ),
        "C_trilateral_plus_interaction": lambda seed: (
            TrilateralWithInteraction(seed=seed)
        ),
        "D_full_proposed_stack": lambda seed: (
            FullProposedStack(seed=seed)
        ),
        "E_full_stack_plus_counterfactual": lambda seed: (
            FullStackPlusCounterfactual(seed=seed)
        ),
    }


# =============================================================================
# Grid sampling
# =============================================================================


_DIRECTIVE_GRIDS: Dict[str, Tuple[Any, ...]] = {
    "user_base_ctr": CTR_GRID,
    "conversion_rate_given_click": CONVERSION_RATE_GRID,
    "interaction_strength": tuple(InteractionStrength),
    "cohort_separation": tuple(CohortSeparation),
    "non_stationarity": tuple(NonStationarityRegime),
    "audience_size_per_cohort": AUDIENCE_SIZE_GRID,
    "impression_rate_per_user_per_week": IMPRESSION_RATE_GRID,
}


def _grid_product_size() -> int:
    return math.prod(len(v) for v in _DIRECTIVE_GRIDS.values())


def generate_full_factorial_configs(
    *,
    base_seed: int = 0,
    audience_cap: Optional[int] = None,
) -> List[SimulationConfig]:
    """Enumerate every combination of the 7 grid values.

    audience_cap optionally clips audience_size_per_cohort to a
    maximum (used in tests + small-scale sweep runs to keep total
    impressions tractable).
    """
    configs: List[SimulationConfig] = []
    keys = list(_DIRECTIVE_GRIDS.keys())
    grids = [_DIRECTIVE_GRIDS[k] for k in keys]
    for ix, combo in enumerate(itertools.product(*grids)):
        kwargs = dict(zip(keys, combo))
        if audience_cap is not None:
            kwargs["audience_size_per_cohort"] = min(
                kwargs["audience_size_per_cohort"], audience_cap,
            )
        configs.append(SimulationConfig(
            seed=int(base_seed) + ix,
            **kwargs,
        ))
    return configs


def generate_lhs_configs(
    *,
    n_samples: int,
    base_seed: int = 0,
    audience_cap: Optional[int] = None,
) -> List[SimulationConfig]:
    """Latin-hypercube-style discrete sampling over the 7 grids.

    For each grid dimension, generate n_samples values stratified
    over the dimension's discrete grid (using uniform random
    selection when n_samples > grid size, weighted-stratified
    when n_samples ≤ grid size). Then random-pair across dimensions
    for the n_samples joint cells.

    Determinism: seeded by base_seed.
    """
    if n_samples < 1:
        return []

    rng = random.Random(int(base_seed))
    keys = list(_DIRECTIVE_GRIDS.keys())

    # Per-dimension sampled-with-replacement values.
    per_dim_samples: Dict[str, List[Any]] = {}
    for k in keys:
        grid = _DIRECTIVE_GRIDS[k]
        # Cycle through the grid stratified, then jitter: ensure
        # every grid value appears at least once when n_samples >=
        # grid size.
        gsz = len(grid)
        stratified: List[Any] = []
        if n_samples <= gsz:
            stratified = list(rng.sample(list(grid), n_samples))
        else:
            for ix in range(n_samples):
                stratified.append(grid[ix % gsz])
            rng.shuffle(stratified)
        per_dim_samples[k] = stratified

    configs: List[SimulationConfig] = []
    for ix in range(n_samples):
        kwargs = {k: per_dim_samples[k][ix] for k in keys}
        if audience_cap is not None:
            kwargs["audience_size_per_cohort"] = min(
                kwargs["audience_size_per_cohort"], audience_cap,
            )
        configs.append(SimulationConfig(
            seed=int(base_seed) + ix,
            **kwargs,
        ))
    return configs


def generate_grid_configs(
    *,
    mode: str = "auto",
    n_samples_lhs: int = 50,
    base_seed: int = 0,
    audience_cap: Optional[int] = None,
    full_factorial_cap: int = FULL_FACTORIAL_CAP,
) -> Tuple[List[SimulationConfig], str]:
    """Route to full-factorial or LHS based on grid product size.

    Returns (configs, mode_used). mode="auto" picks full when product
    ≤ full_factorial_cap; LHS otherwise. mode="full_factorial" or
    "lhs" forces.
    """
    product_size = _grid_product_size()
    if mode == "auto":
        chosen_mode = (
            "full_factorial" if product_size <= full_factorial_cap
            else "lhs"
        )
    else:
        chosen_mode = mode
    if chosen_mode == "full_factorial":
        return (
            generate_full_factorial_configs(
                base_seed=base_seed, audience_cap=audience_cap,
            ),
            "full_factorial",
        )
    return (
        generate_lhs_configs(
            n_samples=n_samples_lhs,
            base_seed=base_seed,
            audience_cap=audience_cap,
        ),
        "lhs",
    )


# =============================================================================
# Per-cell timeseries + result
# =============================================================================


@dataclass(frozen=True)
class TimeseriesSample:
    """One snapshot during a cell's run."""

    impressions_so_far: int
    cumulative_lift: float
    top_mechanism: Optional[str]
    posterior_ci_width_mean: Optional[float]
    hour_of_horizon: float


@dataclass(frozen=True)
class SweepCellResult:
    """Outcome of one (architecture × horizon × sim_config) cell."""

    cell_id: str
    architecture_name: str
    horizon_weeks: int
    sim_config_dict: Dict[str, Any]
    final_cumulative_lift: float
    total_impressions: int
    total_conversions: int
    final_cumulative_conversion_rate: float
    per_mechanism_n: Dict[str, int]
    per_mechanism_conversions: Dict[str, int]
    timeseries: List[TimeseriesSample]
    # Architecture E only — None for A/B/C/D.
    counterfactual_ess: Optional[float] = None
    counterfactual_ess_multiplier: Optional[float] = None
    # mSPRT proxy: # impressions until top mechanism stayed unchanged
    # for STABLE_TOP_ARM_WINDOW consecutive observations. None if not
    # achieved within the run.
    msprt_proxy_stopping_impressions: Optional[int] = None
    # Non-stationarity recovery: hours from regime switch to first
    # cumulative-lift improvement. Computed only when
    # non_stationarity == ABRUPT_SWITCHING; None otherwise.
    non_stationarity_recovery_hours: Optional[float] = None


@dataclass(frozen=True)
class SweepResult:
    """Aggregated result over the full sweep."""

    cells: List[SweepCellResult]
    architectures_compared: List[str]
    horizons_compared: List[int]
    sample_mode: str
    n_grid_points_full: int
    n_cells_total: int
    sweep_started_at_ts: float
    sweep_finished_at_ts: float

    def by_architecture(self) -> Dict[str, List[SweepCellResult]]:
        out: Dict[str, List[SweepCellResult]] = {}
        for c in self.cells:
            out.setdefault(c.architecture_name, []).append(c)
        return out

    def cumulative_lift_distribution(
        self,
    ) -> Dict[str, List[float]]:
        out: Dict[str, List[float]] = {}
        for c in self.cells:
            out.setdefault(c.architecture_name, []).append(
                c.final_cumulative_lift,
            )
        return out

    def msprt_stopping_time_distribution(
        self,
    ) -> Dict[str, List[Optional[int]]]:
        out: Dict[str, List[Optional[int]]] = {}
        for c in self.cells:
            out.setdefault(c.architecture_name, []).append(
                c.msprt_proxy_stopping_impressions,
            )
        return out

    def non_stationarity_recovery_curve(
        self,
    ) -> Dict[str, List[float]]:
        """Per-architecture list of recovery times across cells with
        ABRUPT_SWITCHING regime. Empty list when no such cells in
        the sweep."""
        out: Dict[str, List[float]] = {}
        for c in self.cells:
            if c.non_stationarity_recovery_hours is None:
                continue
            out.setdefault(c.architecture_name, []).append(
                c.non_stationarity_recovery_hours,
            )
        return out

    def counterfactual_ess_multiplier_distribution(
        self,
    ) -> List[float]:
        """ESS multipliers across all cells (only Architecture E
        contributes; others have None)."""
        return [
            c.counterfactual_ess_multiplier
            for c in self.cells
            if c.counterfactual_ess_multiplier is not None
        ]


# =============================================================================
# Metric extractors — invoked at end-of-run per cell
# =============================================================================


def _extract_top_mechanism(arch: Any) -> Optional[str]:
    """Best-guess top arm from the architecture's accumulator state."""
    # Per-mechanism global running mean (A) — pick the highest mean.
    if hasattr(arch, "_mech_n") and hasattr(arch, "_mech_conversions"):
        mech_n = getattr(arch, "_mech_n", {})
        mech_conv = getattr(arch, "_mech_conversions", {})
        if mech_n:
            best_m = None
            best_v = -1.0
            for m in mech_n:
                n = mech_n.get(m, 0)
                if n == 0:
                    continue
                v = mech_conv.get(m, 0) / float(n)
                if v > best_v:
                    best_v = v
                    best_m = m
            return best_m
    # Cohort-level running mean for B/C/D — aggregate across cohorts.
    if hasattr(arch, "_cohort_mech_n"):
        cohort_mech_n = getattr(arch, "_cohort_mech_n", {})
        cohort_mech_conv = getattr(arch, "_cohort_mech_conv", {})
        agg_n: Dict[str, int] = defaultdict(int)
        agg_c: Dict[str, int] = defaultdict(int)
        for (cohort, m), n in cohort_mech_n.items():
            agg_n[m] += n
        for (cohort, m), c in cohort_mech_conv.items():
            agg_c[m] += c
        if agg_n:
            best_m = None
            best_v = -1.0
            for m, n in agg_n.items():
                if n == 0:
                    continue
                v = agg_c.get(m, 0) / float(n)
                if v > best_v:
                    best_v = v
                    best_m = m
            return best_m
    # E composes around an inner FullProposedStack.
    if hasattr(arch, "_inner"):
        return _extract_top_mechanism(arch._inner)
    return None


def _extract_posterior_ci_width_mean(arch: Any) -> Optional[float]:
    """Average per-mechanism posterior 90% CI width across all cells.

    Uses scipy.stats.beta when available; falls back to a Gaussian
    approximation on Beta(α, β) when not. Returns None for
    architectures that don't maintain Beta posteriors (A).
    """
    accumulators = None
    # E composes around inner.
    if hasattr(arch, "_inner"):
        return _extract_posterior_ci_width_mean(arch._inner)
    # B/C/D maintain (cohort, mech) accumulators.
    if hasattr(arch, "_cohort_mech_n") and hasattr(arch, "_cohort_mech_conv"):
        n_dict = getattr(arch, "_cohort_mech_n", {})
        c_dict = getattr(arch, "_cohort_mech_conv", {})
        accumulators = [
            (n_dict.get(k, 0), c_dict.get(k, 0))
            for k in n_dict
        ]
    if accumulators is None or not accumulators:
        return None

    try:
        from scipy import stats
        widths: List[float] = []
        for n, c in accumulators:
            alpha = 1.0 + c
            beta = 1.0 + max(0, n - c)
            # 90% CI via Beta quantiles.
            lo = stats.beta.ppf(0.05, alpha, beta)
            hi = stats.beta.ppf(0.95, alpha, beta)
            widths.append(float(hi - lo))
        return sum(widths) / len(widths) if widths else None
    except Exception:
        # Gaussian approximation: σ ≈ sqrt(αβ / ((α+β)²(α+β+1)));
        # 90% CI ≈ 1.645 × 2 × σ.
        widths_g: List[float] = []
        for n, c in accumulators:
            alpha = 1.0 + c
            beta = 1.0 + max(0, n - c)
            denom = ((alpha + beta) ** 2) * (alpha + beta + 1)
            if denom <= 0:
                continue
            sigma = math.sqrt(alpha * beta / denom)
            widths_g.append(1.645 * 2.0 * sigma)
        return sum(widths_g) / len(widths_g) if widths_g else None


# =============================================================================
# Single-cell run with timeseries
# =============================================================================


def _seed_for_cell(
    base_seed: int,
    architecture_name: str,
    horizon_weeks: int,
    sim_config_seed: int,
) -> int:
    """Deterministic per-cell seed from base + arch hash + horizon
    + config seed. Avoids correlation across cells while keeping
    runs reproducible."""
    return int(base_seed) + (hash(architecture_name) & 0xFFFF) \
        + int(horizon_weeks) * 1009 + int(sim_config_seed)


def _run_one_cell(
    *,
    architecture_name: str,
    architecture_factory: Callable[[int], Architecture],
    horizon_weeks: int,
    sim_config: SimulationConfig,
    base_seed: int,
) -> SweepCellResult:
    """Run one (architecture × horizon × sim_config) cell with
    timeseries instrumentation."""
    # Build a horizon-overridden sim_config (preserves seed).
    cell_config = SimulationConfig(
        user_base_ctr=sim_config.user_base_ctr,
        conversion_rate_given_click=sim_config.conversion_rate_given_click,
        interaction_strength=sim_config.interaction_strength,
        cohort_separation=sim_config.cohort_separation,
        non_stationarity=sim_config.non_stationarity,
        audience_size_per_cohort=sim_config.audience_size_per_cohort,
        impression_rate_per_user_per_week=(
            sim_config.impression_rate_per_user_per_week
        ),
        horizon_weeks=int(horizon_weeks),
        n_cohorts=sim_config.n_cohorts,
        n_mechanisms=sim_config.n_mechanisms,
        seed=sim_config.seed,
    )
    cell_seed = _seed_for_cell(
        base_seed, architecture_name, horizon_weeks, sim_config.seed,
    )
    architecture = architecture_factory(cell_seed)

    population = generate_population(cell_config)
    world = SyntheticWorld(population)
    architecture.configure(population)

    impressions = world.stream_impressions()
    n_imp = len(impressions)
    if n_imp == 0:
        return SweepCellResult(
            cell_id=f"empty-{architecture_name}-h{horizon_weeks}-s{sim_config.seed}",
            architecture_name=architecture_name,
            horizon_weeks=int(horizon_weeks),
            sim_config_dict=_config_to_dict(cell_config),
            final_cumulative_lift=0.0,
            total_impressions=0,
            total_conversions=0,
            final_cumulative_conversion_rate=0.0,
            per_mechanism_n={},
            per_mechanism_conversions={},
            timeseries=[],
        )

    snapshot_indices = _decile_snapshot_indices(
        n_imp, TIMESERIES_SAMPLES_PER_CELL,
    )
    snapshot_indices_set = set(snapshot_indices)
    timeseries: List[TimeseriesSample] = []

    baseline_rate = (
        cell_config.user_base_ctr
        * cell_config.conversion_rate_given_click
    )

    per_mech_n: Dict[str, int] = {}
    per_mech_conv: Dict[str, int] = {}
    total_conv = 0

    # mSPRT-proxy state: track top arm at each impression; record
    # the impression index at which the top arm stayed unchanged
    # for STABLE_TOP_ARM_WINDOW consecutive observations.
    last_top_arm: Optional[str] = None
    consecutive_stable_count: int = 0
    msprt_proxy_stopping: Optional[int] = None

    # Non-stationarity recovery state: only meaningful when
    # ABRUPT_SWITCHING. The world switches at horizon midpoint;
    # we record cumulative_lift just after the switch and look
    # for first impression where post-switch lift exceeds the
    # at-switch baseline.
    is_switching = (
        cell_config.non_stationarity ==
        NonStationarityRegime.ABRUPT_SWITCHING
    )
    switch_hour = (cell_config.horizon_weeks * 168.0) / 2.0
    pre_switch_recorded_rate: Optional[float] = None
    post_switch_recovery_hours: Optional[float] = None

    for ix, imp in enumerate(impressions):
        mech = architecture.select_mechanism(imp)
        outcome = world.deliver_outcome(imp, mech)
        architecture.record_outcome(outcome)

        per_mech_n[mech] = per_mech_n.get(mech, 0) + 1
        if outcome.converted:
            per_mech_conv[mech] = per_mech_conv.get(mech, 0) + 1
            total_conv += 1

        # mSPRT proxy
        cur_top = _extract_top_mechanism(architecture)
        if cur_top is not None and cur_top == last_top_arm:
            consecutive_stable_count += 1
            if (
                msprt_proxy_stopping is None
                and consecutive_stable_count >= STABLE_TOP_ARM_WINDOW
            ):
                msprt_proxy_stopping = ix + 1
        else:
            consecutive_stable_count = 1
            last_top_arm = cur_top

        # Non-stationarity recovery.
        if is_switching:
            cum_rate = total_conv / float(ix + 1)
            if (
                pre_switch_recorded_rate is None
                and imp.hour_of_horizon >= switch_hour
            ):
                pre_switch_recorded_rate = cum_rate
            elif (
                pre_switch_recorded_rate is not None
                and post_switch_recovery_hours is None
                and cum_rate > pre_switch_recorded_rate
            ):
                post_switch_recovery_hours = (
                    imp.hour_of_horizon - switch_hour
                )

        # Timeseries snapshot
        if ix in snapshot_indices_set:
            cum_rate = total_conv / float(ix + 1)
            if baseline_rate > 0:
                cum_lift = (cum_rate - baseline_rate) / baseline_rate
            else:
                cum_lift = 0.0
            ci_width = _extract_posterior_ci_width_mean(architecture)
            timeseries.append(TimeseriesSample(
                impressions_so_far=ix + 1,
                cumulative_lift=cum_lift,
                top_mechanism=cur_top,
                posterior_ci_width_mean=ci_width,
                hour_of_horizon=float(imp.hour_of_horizon),
            ))

    final_rate = total_conv / float(n_imp) if n_imp > 0 else 0.0
    if baseline_rate > 0:
        final_lift = (final_rate - baseline_rate) / baseline_rate
    else:
        final_lift = 0.0

    # Counterfactual ESS for E only.
    counterfactual_ess: Optional[float] = None
    counterfactual_ess_multiplier: Optional[float] = None
    if hasattr(architecture, "effective_sample_size"):
        try:
            ess = float(architecture.effective_sample_size())
            counterfactual_ess = ess
            counterfactual_ess_multiplier = (
                ess / float(n_imp) if n_imp > 0 else 0.0
            )
        except Exception:
            pass

    return SweepCellResult(
        cell_id=(
            f"{architecture_name}-h{horizon_weeks}-"
            f"s{sim_config.seed}-c{cell_seed}"
        ),
        architecture_name=architecture_name,
        horizon_weeks=int(horizon_weeks),
        sim_config_dict=_config_to_dict(cell_config),
        final_cumulative_lift=final_lift,
        total_impressions=n_imp,
        total_conversions=total_conv,
        final_cumulative_conversion_rate=final_rate,
        per_mechanism_n=per_mech_n,
        per_mechanism_conversions=per_mech_conv,
        timeseries=timeseries,
        counterfactual_ess=counterfactual_ess,
        counterfactual_ess_multiplier=counterfactual_ess_multiplier,
        msprt_proxy_stopping_impressions=msprt_proxy_stopping,
        non_stationarity_recovery_hours=post_switch_recovery_hours,
    )


def _decile_snapshot_indices(n: int, k: int) -> List[int]:
    """Pick K indices roughly evenly spaced across [0, n-1]."""
    if n <= 0 or k <= 0:
        return []
    if k >= n:
        return list(range(n))
    step = max(1, n // k)
    out: List[int] = []
    for i in range(k):
        ix = min(n - 1, i * step + step - 1)
        out.append(ix)
    return sorted(set(out))


def _config_to_dict(c: SimulationConfig) -> Dict[str, Any]:
    """Serializable representation. Enums → string values."""
    return {
        "user_base_ctr": c.user_base_ctr,
        "conversion_rate_given_click": c.conversion_rate_given_click,
        "interaction_strength": c.interaction_strength.value,
        "cohort_separation": c.cohort_separation.value,
        "non_stationarity": c.non_stationarity.value,
        "audience_size_per_cohort": c.audience_size_per_cohort,
        "impression_rate_per_user_per_week": (
            c.impression_rate_per_user_per_week
        ),
        "horizon_weeks": c.horizon_weeks,
        "n_cohorts": c.n_cohorts,
        "n_mechanisms": c.n_mechanisms,
        "seed": c.seed,
    }


# =============================================================================
# Sweep runner
# =============================================================================


def run_sweep(
    *,
    architectures: Optional[Dict[str, Callable[[int], Architecture]]] = None,
    horizons: Tuple[int, ...] = (2, 4),
    sample_mode: str = "auto",
    n_samples_lhs: int = 50,
    base_seed: int = 0,
    audience_cap: Optional[int] = None,
) -> SweepResult:
    """Run the full sweep: every (architecture × horizon × sim_config)
    cell.

    Args:
        architectures: name → factory(seed) -> Architecture. Default
            is the canonical A/B/C/D/E lineup.
        horizons: which horizons to sweep. Default (2, 4) — the
            wrap-out hard-stop subset.
        sample_mode: "auto" / "full_factorial" / "lhs".
        n_samples_lhs: when LHS routing fires, this many cells
            per (architecture × horizon) combination.
        base_seed: per-cell seed derivation root.
        audience_cap: optional ceiling on audience_size_per_cohort
            to keep runs tractable in tests / small-scale runs.
    """
    if architectures is None:
        architectures = default_architecture_factories()

    started_at = time.time()

    sim_configs, mode_used = generate_grid_configs(
        mode=sample_mode,
        n_samples_lhs=n_samples_lhs,
        base_seed=base_seed,
        audience_cap=audience_cap,
    )

    cells: List[SweepCellResult] = []
    for arch_name, factory in architectures.items():
        for horizon in horizons:
            for sim_config in sim_configs:
                result = _run_one_cell(
                    architecture_name=arch_name,
                    architecture_factory=factory,
                    horizon_weeks=int(horizon),
                    sim_config=sim_config,
                    base_seed=base_seed,
                )
                cells.append(result)

    finished_at = time.time()

    return SweepResult(
        cells=cells,
        architectures_compared=list(architectures.keys()),
        horizons_compared=list(horizons),
        sample_mode=mode_used,
        n_grid_points_full=_grid_product_size(),
        n_cells_total=len(cells),
        sweep_started_at_ts=started_at,
        sweep_finished_at_ts=finished_at,
    )


# =============================================================================
# Persistence (JSON-lines)
# =============================================================================


def serialize_sweep_result_jsonl(
    result: SweepResult, path: str,
) -> None:
    """Write SweepResult to a JSON-lines artifact.

    Line 0: a header line with sweep-level metadata.
    Lines 1..N: one cell per line.
    Diffable + streaming-friendly + zero new dependencies.
    """
    header = {
        "_record_type": "sweep_header",
        "architectures_compared": list(result.architectures_compared),
        "horizons_compared": list(result.horizons_compared),
        "sample_mode": result.sample_mode,
        "n_grid_points_full": result.n_grid_points_full,
        "n_cells_total": result.n_cells_total,
        "sweep_started_at_ts": result.sweep_started_at_ts,
        "sweep_finished_at_ts": result.sweep_finished_at_ts,
    }
    with open(path, "w") as f:
        f.write(json.dumps(header) + "\n")
        for cell in result.cells:
            line = {"_record_type": "sweep_cell", **asdict(cell)}
            f.write(json.dumps(line) + "\n")


def load_sweep_result_jsonl(path: str) -> SweepResult:
    """Read SweepResult from a JSON-lines artifact. Lossless round-
    trip with serialize_sweep_result_jsonl."""
    cells: List[SweepCellResult] = []
    header: Optional[Dict[str, Any]] = None
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            rec_type = payload.pop("_record_type", None)
            if rec_type == "sweep_header":
                header = payload
            elif rec_type == "sweep_cell":
                # Reconstruct timeseries
                ts_raw = payload.pop("timeseries", []) or []
                timeseries = [TimeseriesSample(**ts) for ts in ts_raw]
                cells.append(SweepCellResult(
                    timeseries=timeseries,
                    **payload,
                ))
    if header is None:
        raise ValueError(f"No sweep_header record in {path}")
    return SweepResult(
        cells=cells,
        architectures_compared=list(header["architectures_compared"]),
        horizons_compared=list(header["horizons_compared"]),
        sample_mode=header["sample_mode"],
        n_grid_points_full=int(header["n_grid_points_full"]),
        n_cells_total=int(header["n_cells_total"]),
        sweep_started_at_ts=float(header["sweep_started_at_ts"]),
        sweep_finished_at_ts=float(header["sweep_finished_at_ts"]),
    )


# =============================================================================
# Summary rendering — directive lines 1166-1171 metrics in tabular form
# =============================================================================


def _avg_or_none(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def sweep_summary(result: SweepResult) -> str:
    """Tabular summary in directive lines 1166-1171 columns:

      - Cumulative lift over baseline (mean across cells)
      - Posterior CI width (mean across cells from end-of-run)
      - mSPRT stopping time (median # impressions to stable best arm)
      - Robustness to non-stationarity (mean recovery hours on
        ABRUPT_SWITCHING cells)
      - Counterfactual-trace ESS multiplier (E only)

    Output is a printable string, one row per architecture.
    """
    by_arch = result.by_architecture()
    rows: List[str] = []
    rows.append(
        "architecture                    | "
        "cum_lift_mean | "
        "ci_width_mean | "
        "mSPRT_stopping_med | "
        "non_stat_recovery_h | "
        "ESS_mult"
    )
    rows.append("-" * 130)
    for arch_name in result.architectures_compared:
        cells = by_arch.get(arch_name, [])
        if not cells:
            continue

        lifts = [c.final_cumulative_lift for c in cells]
        cum_lift = sum(lifts) / len(lifts) if lifts else 0.0

        # End-of-run CI width: take the LAST timeseries sample's
        # ci width per cell, then average.
        end_ci_widths: List[Optional[float]] = []
        for c in cells:
            if c.timeseries:
                end_ci_widths.append(
                    c.timeseries[-1].posterior_ci_width_mean
                )
        ci_mean = _avg_or_none(end_ci_widths)

        msprt_times = [
            c.msprt_proxy_stopping_impressions for c in cells
            if c.msprt_proxy_stopping_impressions is not None
        ]
        msprt_med: Optional[float]
        if msprt_times:
            sorted_times = sorted(msprt_times)
            msprt_med = float(sorted_times[len(sorted_times) // 2])
        else:
            msprt_med = None

        recovery_hours = [
            c.non_stationarity_recovery_hours for c in cells
            if c.non_stationarity_recovery_hours is not None
        ]
        recovery_mean = (
            sum(recovery_hours) / len(recovery_hours)
            if recovery_hours else None
        )

        ess_mults = [
            c.counterfactual_ess_multiplier for c in cells
            if c.counterfactual_ess_multiplier is not None
        ]
        ess_mean = (
            sum(ess_mults) / len(ess_mults)
            if ess_mults else None
        )

        def _fmt(x: Optional[float], width: int = 8) -> str:
            if x is None:
                return "n/a".rjust(width)
            return f"{x:.4f}".rjust(width)

        def _fmt_int(x: Optional[float], width: int = 8) -> str:
            if x is None:
                return "n/a".rjust(width)
            return f"{int(x)}".rjust(width)

        rows.append(
            f"{arch_name:<32}| "
            f"{_fmt(cum_lift, 13)} | "
            f"{_fmt(ci_mean, 13)} | "
            f"{_fmt_int(msprt_med, 18)} | "
            f"{_fmt(recovery_mean, 19)} | "
            f"{_fmt(ess_mean, 8)}"
        )
    return "\n".join(rows)
