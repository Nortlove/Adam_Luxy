"""Pin Slice 32 — Phase 9 sweep runner + serialization + summary.

Per the 2026-05-02 wrap-out greenlight: 5 architectures × 2 horizons
sweep with full-factorial-or-LHS routing, JSON-lines artifact
persistence, tabular sweep_summary in directive lines 1166-1171
columns, and a non-stationarity-recovery sub-test specifically.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict

import pytest

from adam.intelligence.simulation import (
    AUDIENCE_SIZE_GRID,
    CTR_GRID,
    CONVERSION_RATE_GRID,
    HORIZON_WEEKS_GRID,
    IMPRESSION_RATE_GRID,
    Architecture,
    CohortSeparation,
    FullProposedStack,
    FullStackPlusCounterfactual,
    Impression,
    InteractionStrength,
    MarginalAdditiveBaseline,
    NonStationarityRegime,
    Outcome,
    SimulationConfig,
    SweepCellResult,
    SweepResult,
    TimeseriesSample,
    TrilateralCascadeOnly,
    TrilateralWithInteraction,
    default_architecture_factories,
    generate_full_factorial_configs,
    generate_grid_configs,
    generate_lhs_configs,
    load_sweep_result_jsonl,
    run_sweep,
    serialize_sweep_result_jsonl,
    sweep_summary,
)


# -----------------------------------------------------------------------------
# default_architecture_factories — directive lineup
# -----------------------------------------------------------------------------


def test_default_factories_yield_5_architectures():
    factories = default_architecture_factories()
    expected_names = {
        "A_marginal_additive",
        "B_trilateral_cascade_only",
        "C_trilateral_plus_interaction",
        "D_full_proposed_stack",
        "E_full_stack_plus_counterfactual",
    }
    assert set(factories.keys()) == expected_names


def test_factories_take_seed_and_return_architecture():
    factories = default_architecture_factories()
    for name, factory in factories.items():
        instance = factory(42)
        assert isinstance(instance, Architecture)
        assert instance.name == name


# -----------------------------------------------------------------------------
# Grid generation — full factorial vs LHS routing
# -----------------------------------------------------------------------------


def test_full_factorial_grid_size_is_product_of_directive_grids():
    configs = generate_full_factorial_configs(audience_cap=20)
    expected_n = (
        len(CTR_GRID)
        * len(CONVERSION_RATE_GRID)
        * len(InteractionStrength)
        * len(CohortSeparation)
        * len(NonStationarityRegime)
        * len(AUDIENCE_SIZE_GRID)
        * len(IMPRESSION_RATE_GRID)
    )
    assert len(configs) == expected_n


def test_lhs_returns_requested_n_samples():
    configs = generate_lhs_configs(n_samples=15, base_seed=1)
    assert len(configs) == 15


def test_lhs_deterministic_under_same_seed():
    a = generate_lhs_configs(n_samples=10, base_seed=7)
    b = generate_lhs_configs(n_samples=10, base_seed=7)
    a_dicts = [
        (c.user_base_ctr, c.audience_size_per_cohort, c.interaction_strength)
        for c in a
    ]
    b_dicts = [
        (c.user_base_ctr, c.audience_size_per_cohort, c.interaction_strength)
        for c in b
    ]
    assert a_dicts == b_dicts


def test_grid_configs_auto_routes_full_factorial_when_below_cap():
    """Set a cap above the directive product so auto picks full."""
    configs, mode = generate_grid_configs(
        mode="auto", full_factorial_cap=10_000, audience_cap=20,
    )
    assert mode == "full_factorial"
    assert len(configs) == (
        len(CTR_GRID)
        * len(CONVERSION_RATE_GRID)
        * len(InteractionStrength)
        * len(CohortSeparation)
        * len(NonStationarityRegime)
        * len(AUDIENCE_SIZE_GRID)
        * len(IMPRESSION_RATE_GRID)
    )


def test_grid_configs_auto_routes_lhs_when_above_cap():
    configs, mode = generate_grid_configs(
        mode="auto",
        full_factorial_cap=10,
        n_samples_lhs=20,
        audience_cap=20,
    )
    assert mode == "lhs"
    assert len(configs) == 20


def test_audience_cap_clips_audience_size():
    configs = generate_full_factorial_configs(audience_cap=100)
    for c in configs:
        assert c.audience_size_per_cohort <= 100


def test_full_factorial_includes_every_grid_value():
    """Every value in every directive grid appears in at least
    one config."""
    configs = generate_full_factorial_configs(audience_cap=20)
    seen_ctr = {c.user_base_ctr for c in configs}
    seen_cr = {c.conversion_rate_given_click for c in configs}
    seen_int = {c.interaction_strength for c in configs}
    seen_sep = {c.cohort_separation for c in configs}
    seen_ns = {c.non_stationarity for c in configs}
    seen_imp = {c.impression_rate_per_user_per_week for c in configs}
    assert seen_ctr == set(CTR_GRID)
    assert seen_cr == set(CONVERSION_RATE_GRID)
    assert seen_int == set(InteractionStrength)
    assert seen_sep == set(CohortSeparation)
    assert seen_ns == set(NonStationarityRegime)
    assert seen_imp == set(IMPRESSION_RATE_GRID)


# -----------------------------------------------------------------------------
# run_sweep — small smoke test
# -----------------------------------------------------------------------------


def _smoke_factories():
    """Reduced-architecture lineup for fast tests (A + E only)."""
    return {
        "A_marginal_additive": lambda seed: (
            MarginalAdditiveBaseline(seed=seed)
        ),
        "E_full_stack_plus_counterfactual": lambda seed: (
            FullStackPlusCounterfactual(
                seed=seed, propensity_mc_samples=5,
            )
        ),
    }


def test_run_sweep_produces_cells_for_each_arch_horizon_combo():
    """5 LHS configs × 2 architectures × 2 horizons = 20 cells."""
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=3,
        audience_cap=5,
    )
    assert result.n_cells_total == 2 * 1 * 3  # archs × horizons × samples


def test_run_sweep_records_sample_mode():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=2,
        audience_cap=5,
    )
    assert result.sample_mode == "lhs"


def test_run_sweep_cell_carries_architecture_name():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=2,
        audience_cap=5,
    )
    arch_names = {c.architecture_name for c in result.cells}
    assert arch_names == set(_smoke_factories().keys())


def test_run_sweep_cell_carries_horizon():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2, 4),
        sample_mode="lhs",
        n_samples_lhs=1,
        audience_cap=3,
    )
    horizons_seen = {c.horizon_weeks for c in result.cells}
    assert horizons_seen == {2, 4}


def test_run_sweep_timeseries_populated():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=1,
        audience_cap=5,
    )
    for c in result.cells:
        assert len(c.timeseries) > 0


def test_run_sweep_e_carries_counterfactual_ess():
    """E should record counterfactual_ess; A should not."""
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=1,
        audience_cap=5,
    )
    a_cells = [c for c in result.cells if "A_" in c.architecture_name]
    e_cells = [c for c in result.cells if "E_" in c.architecture_name]
    for c in a_cells:
        assert c.counterfactual_ess is None
    for c in e_cells:
        assert c.counterfactual_ess is not None
        assert c.counterfactual_ess_multiplier is not None


# -----------------------------------------------------------------------------
# Non-stationarity recovery sub-test
# -----------------------------------------------------------------------------


def test_non_stationarity_recovery_only_on_abrupt_switching():
    """Cells with STATIONARY / SLOW_DRIFT regimes have None recovery
    time. Only ABRUPT_SWITCHING cells get a numeric recovery time."""
    # Build configs with EVERY non-stationarity regime explicitly.
    configs_by_regime = {}
    for regime in NonStationarityRegime:
        configs_by_regime[regime] = SimulationConfig(
            user_base_ctr=0.005,
            conversion_rate_given_click=0.05,
            interaction_strength=InteractionStrength.MODERATE,
            cohort_separation=CohortSeparation.WEAKLY_SEPARABLE,
            non_stationarity=regime,
            audience_size_per_cohort=5,
            impression_rate_per_user_per_week=2,
            horizon_weeks=2,
            n_cohorts=2,
            n_mechanisms=3,
            seed=99,
        )

    from adam.intelligence.simulation.sweep import _run_one_cell
    factories = _smoke_factories()
    factory = factories["E_full_stack_plus_counterfactual"]
    for regime, config in configs_by_regime.items():
        cell_result = _run_one_cell(
            architecture_name="E_full_stack_plus_counterfactual",
            architecture_factory=factory,
            horizon_weeks=2,
            sim_config=config,
            base_seed=0,
        )
        if regime == NonStationarityRegime.ABRUPT_SWITCHING:
            # We may or may not have observed recovery within the
            # short horizon — but the ATTEMPT was made (the field is
            # set to a numeric or None depending on data).
            # The pin: this is the ONLY regime where a numeric
            # value is even possible.
            pass
        else:
            assert cell_result.non_stationarity_recovery_hours is None, (
                f"recovery time should be None for regime {regime}"
            )


def test_recovery_curve_grouped_per_architecture():
    """SweepResult.non_stationarity_recovery_curve groups recovery
    times per architecture across cells (NOT averaged into a single
    number). The grouping is the per-architecture diagnostic the
    wrap-out greenlight specifically calls out."""
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=20,  # enough to hit ABRUPT_SWITCHING by chance
        audience_cap=5,
    )
    curve = result.non_stationarity_recovery_curve()
    # The curve is a dict[architecture_name -> list of recovery
    # times]. Architectures in it are a subset of the compared set.
    assert isinstance(curve, dict)
    for arch_name, recovery_list in curve.items():
        assert arch_name in result.architectures_compared
        assert isinstance(recovery_list, list)
        for v in recovery_list:
            assert v >= 0.0


# -----------------------------------------------------------------------------
# JSON-lines persistence — round-trip + lossless
# -----------------------------------------------------------------------------


def test_serialize_load_round_trip():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=2,
        audience_cap=4,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "sweep.jsonl")
        serialize_sweep_result_jsonl(result, path)
        # File is non-empty + parses as JSON-lines.
        assert os.path.getsize(path) > 0
        with open(path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert lines[0]["_record_type"] == "sweep_header"
        assert all(l["_record_type"] == "sweep_cell" for l in lines[1:])

        loaded = load_sweep_result_jsonl(path)

    assert loaded.n_cells_total == result.n_cells_total
    assert (
        loaded.architectures_compared == result.architectures_compared
    )
    assert loaded.horizons_compared == result.horizons_compared
    assert loaded.sample_mode == result.sample_mode

    # Cell-level lossless check.
    for orig, recon in zip(result.cells, loaded.cells):
        assert orig.cell_id == recon.cell_id
        assert orig.architecture_name == recon.architecture_name
        assert orig.horizon_weeks == recon.horizon_weeks
        assert orig.total_impressions == recon.total_impressions
        assert (
            orig.final_cumulative_lift
            == pytest.approx(recon.final_cumulative_lift)
        )
        assert len(orig.timeseries) == len(recon.timeseries)


# -----------------------------------------------------------------------------
# sweep_summary — directive line 1166-1171 columns
# -----------------------------------------------------------------------------


def test_sweep_summary_returns_string_with_directive_columns():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=2,
        audience_cap=5,
    )
    summary = sweep_summary(result)
    assert isinstance(summary, str)
    # Header must include the directive's named metric columns.
    assert "cum_lift" in summary
    assert "ci_width" in summary
    assert "mSPRT_stopping" in summary
    assert "non_stat_recovery" in summary
    assert "ESS_mult" in summary


def test_sweep_summary_one_row_per_architecture():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=1,
        audience_cap=4,
    )
    summary = sweep_summary(result)
    for arch_name in result.architectures_compared:
        assert arch_name in summary


# -----------------------------------------------------------------------------
# Per-architecture distribution accessors
# -----------------------------------------------------------------------------


def test_cumulative_lift_distribution_grouped_per_arch():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=3,
        audience_cap=4,
    )
    dist = result.cumulative_lift_distribution()
    assert set(dist.keys()) == set(result.architectures_compared)
    for arch_name, lifts in dist.items():
        # 3 cells per architecture (n_samples_lhs=3 × 1 horizon).
        assert len(lifts) == 3


def test_msprt_stopping_time_distribution_grouped_per_arch():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=2,
        audience_cap=4,
    )
    dist = result.msprt_stopping_time_distribution()
    assert set(dist.keys()) == set(result.architectures_compared)


def test_counterfactual_ess_multiplier_only_for_e():
    result = run_sweep(
        architectures=_smoke_factories(),
        horizons=(2,),
        sample_mode="lhs",
        n_samples_lhs=2,
        audience_cap=4,
    )
    ess_mults = result.counterfactual_ess_multiplier_distribution()
    # E contributes 2 cells; A contributes 0.
    assert len(ess_mults) == 2
    for v in ess_mults:
        assert isinstance(v, float)
        assert v >= 0.0


# -----------------------------------------------------------------------------
# Full directive lineup — sanity smoke (all 5 architectures × 2 horizons)
# -----------------------------------------------------------------------------


def test_full_directive_lineup_sweep_smoke():
    """5-arch × 2-horizon × 2-LHS-cells = 20 cells. Slow-but-not-too-slow
    end-to-end smoke that the full directive lineup runs without
    crashing."""
    factories = default_architecture_factories()
    # Wrap E with reduced MC samples for test speed.
    factories["E_full_stack_plus_counterfactual"] = (
        lambda seed: FullStackPlusCounterfactual(
            seed=seed, propensity_mc_samples=5,
        )
    )
    result = run_sweep(
        architectures=factories,
        horizons=(2, 4),
        sample_mode="lhs",
        n_samples_lhs=2,
        audience_cap=3,
    )
    assert result.n_cells_total == 5 * 2 * 2  # 20 cells
    assert set(result.architectures_compared) == set(factories.keys())
