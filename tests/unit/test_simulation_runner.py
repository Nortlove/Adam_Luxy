"""Pin Slice 25 — Phase 9 simulation framework START commit.

Per directive Appendix A + 2026-05-02 wrap-out hard-stop criterion
(i): the simulation must run end-to-end on at least the 5-architecture
× 2-horizon subset before v3 Phase 1. This slice ships the substrate
+ Architecture A baseline + the runner; subsequent slices add B-E.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Phase 9 + Appendix A lines 1148-1173
        (variables, architectures, metrics) + 2026-05-02 wrap-out
        handoff (highest priority arc).

    (b) Boundary anchors:
          - Config grid values match directive Appendix A enumerations
          - SyntheticUser carries TRUE per-mechanism efficacy +
            carryover ρ
          - Population generation deterministic from seed
          - World stream_impressions count = users × rate × weeks
          - World honors carryover (positive ρ + recent same-mech →
            reduced effective efficacy)
          - World honors non-stationarity regimes (drift / abrupt switch)
          - Architecture A satisfies Protocol; cold-start covers
            untried mechanisms before exploiting
          - Runner returns SimulationResult with cumulative metrics
            + per-mechanism breakdown

    (c) calibration_pending=True. Architecture A's epsilon (0.10),
        the world's true carryover τ (24h), and the population's
        cohort-offset drift signal-to-noise are all v0.1 conservative
        choices. A14 flag: PHASE_9_SIM_CALIBRATION_PILOT_PENDING.

    (d) Honest tags — what is NOT in this slice (named successors):
          - Architectures B, C, D, E (sibling slices)
          - Per-cohort uplift CI width metric
          - Time-to-confident-best-arm (mSPRT stopping time)
          - Robustness-to-non-stationarity recovery time
          - Counterfactual-trace efficiency multiplier (Architecture E)
          - Full-factorial sweep runner + LHS sampler
          - Aggregation into the "order of marginal contribution"
            report named in Appendix A line 1173
"""

from __future__ import annotations

import random

import pytest

from adam.intelligence.simulation import (
    Architecture,
    CohortSeparation,
    Impression,
    InteractionStrength,
    MarginalAdditiveBaseline,
    NonStationarityRegime,
    Outcome,
    SimulationConfig,
    SimulationResult,
    SyntheticPopulation,
    SyntheticUser,
    SyntheticWorld,
    generate_population,
    run_single_cell,
)


# -----------------------------------------------------------------------------
# Config grid contracts
# -----------------------------------------------------------------------------


def test_directive_grid_values_present():
    from adam.intelligence.simulation.config import (
        AUDIENCE_SIZE_GRID,
        CONVERSION_RATE_GRID,
        CTR_GRID,
        HORIZON_WEEKS_GRID,
        IMPRESSION_RATE_GRID,
    )
    assert CTR_GRID == (0.0005, 0.0015, 0.005)
    assert CONVERSION_RATE_GRID == (0.005, 0.02, 0.05)
    assert IMPRESSION_RATE_GRID == (2, 7, 20)
    assert AUDIENCE_SIZE_GRID == (500, 2_000, 10_000)
    assert HORIZON_WEEKS_GRID == (2, 4, 6)


def test_interaction_strength_enum_complete():
    expected = {"none", "weak", "moderate", "strong"}
    assert {e.value for e in InteractionStrength} == expected


def test_cohort_separation_enum_complete():
    expected = {
        "indistinguishable", "weakly_separable", "strongly_separable",
    }
    assert {e.value for e in CohortSeparation} == expected


def test_non_stationarity_regime_enum_complete():
    expected = {"stationary", "slow_drift", "abrupt_switching"}
    assert {e.value for e in NonStationarityRegime} == expected


def test_simulation_config_frozen():
    config = SimulationConfig(
        user_base_ctr=0.001,
        conversion_rate_given_click=0.01,
        interaction_strength=InteractionStrength.WEAK,
        cohort_separation=CohortSeparation.WEAKLY_SEPARABLE,
        non_stationarity=NonStationarityRegime.STATIONARY,
        audience_size_per_cohort=100,
        impression_rate_per_user_per_week=2,
    )
    with pytest.raises((AttributeError, Exception)):
        config.user_base_ctr = 999.0  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Population generation
# -----------------------------------------------------------------------------


def _small_config(**overrides) -> SimulationConfig:
    """Test-sized config — small enough for fast unit tests."""
    defaults = dict(
        user_base_ctr=0.005,
        conversion_rate_given_click=0.05,
        interaction_strength=InteractionStrength.MODERATE,
        cohort_separation=CohortSeparation.STRONGLY_SEPARABLE,
        non_stationarity=NonStationarityRegime.STATIONARY,
        audience_size_per_cohort=10,
        impression_rate_per_user_per_week=2,
        horizon_weeks=2,
        n_cohorts=2,
        n_mechanisms=3,
        seed=42,
    )
    defaults.update(overrides)
    return SimulationConfig(**defaults)


def test_population_size_matches_config():
    config = _small_config()
    pop = generate_population(config)
    assert len(pop.users) == config.audience_size_per_cohort * config.n_cohorts


def test_population_has_n_mechanisms_in_efficacy_dict():
    config = _small_config()
    pop = generate_population(config)
    for u in pop.users:
        assert len(u.true_mechanism_efficacy) == config.n_mechanisms


def test_population_deterministic_under_same_seed():
    a = generate_population(_small_config(seed=123))
    b = generate_population(_small_config(seed=123))
    for ua, ub in zip(a.users, b.users):
        assert ua.user_id == ub.user_id
        assert ua.true_mechanism_efficacy == ub.true_mechanism_efficacy
        assert ua.true_carryover_rho == ub.true_carryover_rho


def test_population_different_seeds_different_efficacy():
    a = generate_population(_small_config(seed=1))
    b = generate_population(_small_config(seed=2))
    diffs = sum(
        1 for ua, ub in zip(a.users, b.users)
        if ua.true_mechanism_efficacy != ub.true_mechanism_efficacy
    )
    assert diffs > 0


def test_population_efficacy_bounded():
    """All efficacy values clipped to [1e-4, 0.5]."""
    config = _small_config(interaction_strength=InteractionStrength.STRONG)
    pop = generate_population(config)
    for u in pop.users:
        for v in u.true_mechanism_efficacy.values():
            assert 1e-4 <= v <= 0.5


def test_population_by_cohort_groups_users():
    config = _small_config()
    pop = generate_population(config)
    by_cohort = pop.by_cohort()
    assert len(by_cohort) == config.n_cohorts
    for cohort_users in by_cohort.values():
        assert len(cohort_users) == config.audience_size_per_cohort


# -----------------------------------------------------------------------------
# Synthetic world
# -----------------------------------------------------------------------------


def test_world_stream_impressions_count():
    config = _small_config()
    pop = generate_population(config)
    world = SyntheticWorld(pop)
    impressions = world.stream_impressions()
    expected = (
        config.audience_size_per_cohort
        * config.n_cohorts
        * config.impression_rate_per_user_per_week
        * config.horizon_weeks
    )
    assert len(impressions) == expected


def test_world_impressions_time_ordered():
    """Stream is monotonically non-decreasing in hour_of_horizon."""
    config = _small_config()
    pop = generate_population(config)
    world = SyntheticWorld(pop)
    impressions = world.stream_impressions()
    for a, b in zip(impressions, impressions[1:]):
        assert a.hour_of_horizon <= b.hour_of_horizon


def test_world_deliver_outcome_uses_true_efficacy_at_high_efficacy():
    """When TRUE efficacy ≈ 0.5 and we run many impressions for one
    user, the realized conversion rate trends toward true efficacy."""
    config = _small_config(seed=7)
    # Build a single user with known high efficacy.
    user = SyntheticUser(
        user_id="u-1", cohort_id=0,
        true_mechanism_efficacy={"social_proof": 0.5},
        true_carryover_rho=0.0,
    )
    pop = SyntheticPopulation(
        users=[user], mechanisms=["social_proof"], n_cohorts=1,
        config=config,
    )
    world = SyntheticWorld(pop)

    # Hand-craft impressions far enough apart that carryover ≈ 0.
    n = 1000
    converts = 0
    for i in range(n):
        imp = Impression(
            impression_id=f"i-{i}", user_id="u-1",
            week=0, hour_of_horizon=float(i * 100),  # 100h apart
        )
        out = world.deliver_outcome(imp, "social_proof")
        if out.converted:
            converts += 1

    realized_rate = converts / n
    # Loose 95% CI bound on Bernoulli(0.5) over n=1000.
    assert 0.42 <= realized_rate <= 0.58


def test_world_carryover_reduces_efficacy_for_repeated_same_mechanism():
    """Same-mechanism touches close together with positive ρ should
    yield FEWER conversions than the no-carryover null."""
    config = _small_config(seed=99)
    user_with_rho = SyntheticUser(
        user_id="u-rho", cohort_id=0,
        true_mechanism_efficacy={"social_proof": 0.4},
        true_carryover_rho=0.95,  # strong positive carryover
    )
    pop = SyntheticPopulation(
        users=[user_with_rho], mechanisms=["social_proof"], n_cohorts=1,
        config=config,
    )
    world = SyntheticWorld(pop)

    # Hammer same mechanism with closely-spaced touches (Δ = 0.1h).
    n = 500
    converts = 0
    for i in range(n):
        imp = Impression(
            impression_id=f"i-{i}", user_id="u-rho",
            week=0, hour_of_horizon=float(i) * 0.1,
        )
        out = world.deliver_outcome(imp, "social_proof")
        if out.converted:
            converts += 1

    rate_with_carryover = converts / n
    # With ρ=0.95 and rapid same-mech repetition, observed rate must
    # be substantially BELOW the bare-touch efficacy 0.4.
    assert rate_with_carryover < 0.40


# -----------------------------------------------------------------------------
# Architecture A baseline
# -----------------------------------------------------------------------------


def test_architecture_a_implements_protocol():
    arch = MarginalAdditiveBaseline()
    assert isinstance(arch, Architecture)


def test_architecture_a_cold_start_explores_all_mechanisms_first():
    """Until each mechanism has at least one observation, A picks
    only from the untried set."""
    config = _small_config()
    pop = generate_population(config)
    arch = MarginalAdditiveBaseline(seed=1)
    arch.configure(pop)

    selected: list = []
    for i, mech in enumerate(pop.mechanisms):
        imp = Impression(
            impression_id=f"i-{i}", user_id="u",
            week=0, hour_of_horizon=float(i),
        )
        sel = arch.select_mechanism(imp)
        selected.append(sel)
        # Record a synthetic outcome.
        arch.record_outcome(Outcome(
            impression_id=imp.impression_id, user_id="u",
            week=0, hour_of_horizon=float(i),
            mechanism_sent=sel, converted=False,
        ))

    # All mechanisms tried at least once.
    assert set(selected) == set(pop.mechanisms)


def test_architecture_a_exploits_best_after_warm_up():
    """After enough observations make one mechanism clearly dominant,
    ε-greedy picks it most of the time."""
    config = _small_config()
    pop = generate_population(config)
    arch = MarginalAdditiveBaseline(epsilon=0.10, seed=42)
    arch.configure(pop)

    # Hand-feed many (mechanism, converted) outcomes — make
    # social_proof the dominant arm.
    target_mech = "social_proof"
    if target_mech not in pop.mechanisms:
        target_mech = pop.mechanisms[0]

    for i in range(200):
        # Cycle through every mechanism a few times for cold-start;
        # then bias outcomes so target_mech's mean is highest.
        mech = pop.mechanisms[i % len(pop.mechanisms)]
        converted = (mech == target_mech and i > 20 and i % 2 == 0)
        arch.record_outcome(Outcome(
            impression_id=f"i-{i}", user_id="u",
            week=0, hour_of_horizon=float(i),
            mechanism_sent=mech, converted=converted,
        ))

    # Now select 200 times and count target hits — ε-greedy with
    # ε=0.1 should pick the dominant arm most of the time.
    n_hits = 0
    n_picks = 200
    for i in range(n_picks):
        imp = Impression(
            impression_id=f"e-{i}", user_id="u",
            week=0, hour_of_horizon=float(i),
        )
        sel = arch.select_mechanism(imp)
        if sel == target_mech:
            n_hits += 1
    # At least 60% target hits (1-ε / |mechanisms| floor + ε noise).
    assert n_hits / n_picks > 0.60


# -----------------------------------------------------------------------------
# Runner — end-to-end one cell
# -----------------------------------------------------------------------------


def test_runner_returns_simulation_result():
    config = _small_config()
    arch = MarginalAdditiveBaseline(seed=0)
    result = run_single_cell(config, arch)
    assert isinstance(result, SimulationResult)
    assert result.architecture_name == "A_marginal_additive"
    assert result.horizon_weeks == config.horizon_weeks


def test_runner_total_impressions_matches_world_stream():
    config = _small_config()
    arch = MarginalAdditiveBaseline(seed=0)
    result = run_single_cell(config, arch)
    expected = (
        config.audience_size_per_cohort
        * config.n_cohorts
        * config.impression_rate_per_user_per_week
        * config.horizon_weeks
    )
    assert result.total_impressions == expected


def test_runner_per_mechanism_n_sums_to_total():
    config = _small_config()
    arch = MarginalAdditiveBaseline(seed=0)
    result = run_single_cell(config, arch)
    assert sum(result.per_mechanism_n.values()) == result.total_impressions


def test_runner_per_mechanism_conversions_sum_to_total():
    config = _small_config()
    arch = MarginalAdditiveBaseline(seed=0)
    result = run_single_cell(config, arch)
    assert (
        sum(result.per_mechanism_conversions.values())
        == result.total_conversions
    )


def test_runner_lift_metric_in_reasonable_range():
    """The lift metric is (rate - baseline) / baseline. For A on a
    moderate-interaction config, lift should be small but reportable
    (not NaN, not extreme)."""
    config = _small_config()
    arch = MarginalAdditiveBaseline(seed=0)
    result = run_single_cell(config, arch)
    # Lift should be a finite float in a wide but reasonable range.
    assert -1.0 <= result.cumulative_lift_over_baseline <= 50.0


def test_runner_simulation_result_frozen():
    config = _small_config()
    arch = MarginalAdditiveBaseline(seed=0)
    result = run_single_cell(config, arch)
    with pytest.raises((AttributeError, Exception)):
        result.total_impressions = 999  # type: ignore[misc]


def test_runner_deterministic_under_same_seed():
    config_a = _small_config(seed=7)
    arch_a = MarginalAdditiveBaseline(seed=7)
    result_a = run_single_cell(config_a, arch_a)

    config_b = _small_config(seed=7)
    arch_b = MarginalAdditiveBaseline(seed=7)
    result_b = run_single_cell(config_b, arch_b)

    assert result_a.total_impressions == result_b.total_impressions
    assert result_a.total_conversions == result_b.total_conversions
    assert result_a.per_mechanism_n == result_b.per_mechanism_n
