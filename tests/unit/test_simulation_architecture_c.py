"""Pin Slice 29 — Architecture C (trilateral + interaction tensor).

Per directive Appendix A line 1162. Architecture C's differentiator
over B: B uses FIXED additive weights between user and cohort
signals; C uses Bayesian shrinkage so the per-(user, mechanism)
interaction cell earns more weight as data accumulates.
"""

from __future__ import annotations

import pytest

from adam.intelligence.simulation import (
    Architecture,
    CohortSeparation,
    Impression,
    InteractionStrength,
    NonStationarityRegime,
    Outcome,
    SimulationConfig,
    TrilateralCascadeOnly,
    TrilateralWithInteraction,
    generate_population,
    run_single_cell,
)


def _config(**overrides) -> SimulationConfig:
    defaults = dict(
        user_base_ctr=0.005,
        conversion_rate_given_click=0.05,
        interaction_strength=InteractionStrength.STRONG,
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


# -----------------------------------------------------------------------------
# Protocol + name + parameters
# -----------------------------------------------------------------------------


def test_architecture_c_satisfies_protocol():
    arch = TrilateralWithInteraction()
    assert isinstance(arch, Architecture)


def test_architecture_c_has_canonical_name():
    arch = TrilateralWithInteraction()
    assert arch.name == "C_trilateral_plus_interaction"


def test_c_default_shrinkage_kappa_is_20():
    arch = TrilateralWithInteraction()
    assert arch.shrinkage_kappa == 20.0


def test_c_negative_or_zero_kappa_raises():
    with pytest.raises(ValueError):
        TrilateralWithInteraction(shrinkage_kappa=0.0)
    with pytest.raises(ValueError):
        TrilateralWithInteraction(shrinkage_kappa=-1.0)


def test_c_custom_kappa_accepted():
    arch = TrilateralWithInteraction(shrinkage_kappa=5.0)
    assert arch.shrinkage_kappa == 5.0


# -----------------------------------------------------------------------------
# Shrinkage weight contract
# -----------------------------------------------------------------------------


def test_c_shrinkage_weight_at_zero_observations_is_zero():
    """No per-user data → weight on user signal = 0 → score collapses
    to cohort prior."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralWithInteraction(seed=1)
    arch.configure(pop)
    user = pop.users[0]
    mech = pop.mechanisms[0]
    assert arch.shrinkage_weight(user.user_id, mech) == 0.0


def test_c_shrinkage_weight_approaches_one_at_high_n():
    """As n_user → ∞, weight → 1 → score captures full per-user
    interaction. At n_user = κ, weight = 0.5 (half-shrinkage point)."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralWithInteraction(shrinkage_kappa=20.0, seed=1)
    arch.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]

    # n_user = 20 (= κ) → weight = 0.5
    arch._user_mech_n[(user.user_id, mech)] = 20
    assert arch.shrinkage_weight(user.user_id, mech) == pytest.approx(0.5)

    # n_user = 200 (= 10κ) → weight = 200/220 ≈ 0.909
    arch._user_mech_n[(user.user_id, mech)] = 200
    assert arch.shrinkage_weight(user.user_id, mech) == pytest.approx(
        200 / 220, rel=1e-6,
    )

    # n_user = 100000 (>> κ) → weight ≈ 1.0
    arch._user_mech_n[(user.user_id, mech)] = 100_000
    assert arch.shrinkage_weight(user.user_id, mech) > 0.999


def test_c_score_at_zero_user_data_collapses_to_cohort_rate():
    config = _config()
    pop = generate_population(config)
    arch = TrilateralWithInteraction(seed=1)
    arch.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]
    cohort = user.cohort_id

    arch._cohort_mech_n[(cohort, mech)] = 50
    arch._cohort_mech_conv[(cohort, mech)] = 20

    score = arch._interaction_score(user.user_id, mech)
    expected_cohort_rate = (1 + 20) / float(2 + 50)
    assert score == pytest.approx(expected_cohort_rate)


def test_c_score_at_high_user_data_dominated_by_user_cell():
    """High n_user → score ≈ user rate (interaction cell captures
    the per-user heterogeneity that B's fixed-weight cannot)."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralWithInteraction(shrinkage_kappa=10.0, seed=1)
    arch.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]
    cohort = user.cohort_id

    # User has TONS of observations on this mechanism → cell signal
    # dominates regardless of cohort.
    arch._user_mech_n[(user.user_id, mech)] = 1000
    arch._user_mech_conv[(user.user_id, mech)] = 800
    # Cohort signal is opposite — low rate.
    arch._cohort_mech_n[(cohort, mech)] = 50
    arch._cohort_mech_conv[(cohort, mech)] = 5

    score = arch._interaction_score(user.user_id, mech)
    # Should be very close to user rate (≈ 801/1002 ≈ 0.799), not
    # cohort rate (≈ 6/52 ≈ 0.115).
    expected_user_rate = (1 + 800) / float(2 + 1000)
    assert score == pytest.approx(expected_user_rate, abs=0.01)


def test_c_score_at_kappa_observations_is_average_of_cells():
    """At n_user = κ, weight = 0.5 → score is exactly the average
    of user_rate and cohort_rate (the defining shrinkage anchor)."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralWithInteraction(shrinkage_kappa=10.0, seed=1)
    arch.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]
    cohort = user.cohort_id

    arch._user_mech_n[(user.user_id, mech)] = 10  # = κ → weight 0.5
    arch._user_mech_conv[(user.user_id, mech)] = 8
    arch._cohort_mech_n[(cohort, mech)] = 100
    arch._cohort_mech_conv[(cohort, mech)] = 10

    user_rate = (1 + 8) / float(2 + 10)
    cohort_rate = (1 + 10) / float(2 + 100)
    expected = 0.5 * user_rate + 0.5 * cohort_rate

    actual = arch._interaction_score(user.user_id, mech)
    assert actual == pytest.approx(expected)


# -----------------------------------------------------------------------------
# Cold-start
# -----------------------------------------------------------------------------


def test_c_cold_start_explores_all_cohort_x_mechanism_cells():
    config = _config()
    pop = generate_population(config)
    arch = TrilateralWithInteraction(seed=11)
    arch.configure(pop)

    by_cohort = pop.by_cohort()
    user_per_cohort = {c: us[0] for c, us in by_cohort.items()}
    for cohort, user in user_per_cohort.items():
        seen: set = set()
        for i, m in enumerate(pop.mechanisms):
            imp = Impression(
                impression_id=f"i-{cohort}-{i}", user_id=user.user_id,
                week=0, hour_of_horizon=float(i),
            )
            sel = arch.select_mechanism(imp)
            seen.add(sel)
            arch.record_outcome(Outcome(
                impression_id=imp.impression_id, user_id=user.user_id,
                week=0, hour_of_horizon=float(i),
                mechanism_sent=sel, converted=False,
            ))
        assert seen == set(pop.mechanisms)


# -----------------------------------------------------------------------------
# Architectural boundary — B vs C
# -----------------------------------------------------------------------------


def test_c_diverges_from_b_at_high_user_data():
    """Pin the B vs C architectural boundary. B uses FIXED 0.5/0.5
    weighting; C uses shrinkage. With identical (user, cohort) stats
    + n_user >> κ, C's score should equal user_rate (interaction-
    captured), while B's stays at 0.5 × user_rate + 0.5 × cohort_rate
    regardless of n. Different scores → different selections."""
    config = _config()
    pop = generate_population(config)
    arch_b = TrilateralCascadeOnly(seed=1)
    arch_c = TrilateralWithInteraction(shrinkage_kappa=10.0, seed=1)
    arch_b.configure(pop)
    arch_c.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]
    cohort = user.cohort_id

    # Heavy per-user data, contradicting the cohort signal.
    for arch in (arch_b, arch_c):
        arch._user_mech_n[(user.user_id, mech)] = 500
        arch._user_mech_conv[(user.user_id, mech)] = 400
        arch._cohort_mech_n[(cohort, mech)] = 50
        arch._cohort_mech_conv[(cohort, mech)] = 5

    score_b = arch_b._trilateral_score(user.user_id, mech)
    score_c = arch_c._interaction_score(user.user_id, mech)
    # B is anchored to fixed 0.5/0.5 → average of user (high) + cohort
    # (low). C with high n_user collapses near user (high). C should
    # be substantially HIGHER than B in this scenario.
    assert score_c > score_b + 0.05, (
        f"C should weight the interaction cell more heavily at high "
        f"n_user (got C={score_c:.4f} vs B={score_b:.4f})"
    )


# -----------------------------------------------------------------------------
# record_outcome
# -----------------------------------------------------------------------------


def test_c_record_outcome_increments_user_and_cohort_stats():
    config = _config()
    pop = generate_population(config)
    arch = TrilateralWithInteraction(seed=1)
    arch.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]
    cohort = user.cohort_id

    arch.record_outcome(Outcome(
        impression_id="i", user_id=user.user_id,
        week=0, hour_of_horizon=0.0,
        mechanism_sent=mech, converted=True,
    ))
    assert arch._user_mech_n[(user.user_id, mech)] == 1
    assert arch._user_mech_conv[(user.user_id, mech)] == 1
    assert arch._cohort_mech_n[(cohort, mech)] == 1
    assert arch._cohort_mech_conv[(cohort, mech)] == 1


# -----------------------------------------------------------------------------
# Runner end-to-end
# -----------------------------------------------------------------------------


def test_c_runner_round_trip():
    config = _config()
    arch = TrilateralWithInteraction(seed=0)
    result = run_single_cell(config, arch)
    assert result.architecture_name == "C_trilateral_plus_interaction"
    assert result.total_impressions > 0


def test_c_runner_deterministic_under_same_seed():
    a = run_single_cell(_config(seed=7), TrilateralWithInteraction(seed=7))
    b = run_single_cell(_config(seed=7), TrilateralWithInteraction(seed=7))
    assert a.total_impressions == b.total_impressions
    assert a.total_conversions == b.total_conversions
    assert a.per_mechanism_n == b.per_mechanism_n
