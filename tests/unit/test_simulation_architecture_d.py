"""Pin Slice 30 — Architecture D (full proposed stack — Spines #1, #2, #4, #5, #7).

Per directive Appendix A line 1163. D's differentiators over C:
  * Spine #1 full-Bayesian: Thompson Sampling on Beta posteriors.
  * Spine #2: AR(1) carryover correction at decision time.

Spine #5 free-energy and Spine #7 cohort-discovery are limited in
v0.1 (synthetic world doesn't expose posture features; cohort
discovery blocked on Loop B). Honest tags in the architecture
class document the boundaries.
"""

from __future__ import annotations

import pytest

from adam.intelligence.simulation import (
    Architecture,
    CohortSeparation,
    FullProposedStack,
    Impression,
    InteractionStrength,
    NonStationarityRegime,
    Outcome,
    SimulationConfig,
    TrilateralWithInteraction,
    generate_population,
    run_single_cell,
)


def _config(**overrides) -> SimulationConfig:
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


# -----------------------------------------------------------------------------
# Protocol + name + parameters
# -----------------------------------------------------------------------------


def test_architecture_d_satisfies_protocol():
    arch = FullProposedStack()
    assert isinstance(arch, Architecture)


def test_architecture_d_has_canonical_name():
    arch = FullProposedStack()
    assert arch.name == "D_full_proposed_stack"


def test_d_default_carryover_rho_and_tau():
    arch = FullProposedStack()
    assert arch.carryover_rho == 0.30
    assert arch.carryover_tau_hours == 24.0


def test_d_zero_or_negative_kappa_raises():
    with pytest.raises(ValueError):
        FullProposedStack(shrinkage_kappa=0.0)


def test_d_zero_or_negative_tau_raises():
    with pytest.raises(ValueError):
        FullProposedStack(carryover_tau_hours=0.0)


# -----------------------------------------------------------------------------
# Carryover correction (Spine #2)
# -----------------------------------------------------------------------------


def test_d_carryover_zero_when_no_history():
    """Cold buyer (no touch history) → zero penalty."""
    arch = FullProposedStack(seed=1)
    config = _config()
    pop = generate_population(config)
    arch.configure(pop)

    pen = arch.carryover_penalty(
        user_id="u-cold",
        mechanism="social_proof",
        week=0,
        hour_of_horizon=0.0,
    )
    assert pen == 0.0


def test_d_carryover_zero_for_cross_mechanism():
    """Recent touch on DIFFERENT mechanism → zero penalty for the
    candidate (Spine #2 is per-mechanism)."""
    arch = FullProposedStack(seed=1)
    config = _config()
    pop = generate_population(config)
    arch.configure(pop)
    user = pop.users[0]

    # Plant a touch on scarcity 1 hour ago.
    arch._touch_history[user.user_id].append((0, 0.0, "scarcity"))

    pen = arch.carryover_penalty(
        user_id=user.user_id,
        mechanism="social_proof",  # different mechanism
        week=0,
        hour_of_horizon=1.0,
    )
    assert pen == 0.0


def test_d_carryover_positive_for_recent_same_mechanism():
    """Recent same-mech touch → positive penalty (decays from
    posterior_mean × ρ × exp(-Δ/τ))."""
    arch = FullProposedStack(carryover_rho=0.5, carryover_tau_hours=10.0, seed=1)
    config = _config()
    pop = generate_population(config)
    arch.configure(pop)
    user = pop.users[0]

    # Plant: a touch on social_proof at hour 0; we're at hour 5h
    # → Δ=5h, τ=10h, decay = exp(-0.5) ≈ 0.607.
    arch._touch_history[user.user_id].append((0, 0.0, "social_proof"))

    # Set the user's posterior mean by injecting some observations.
    arch._user_mech_n[(user.user_id, "social_proof")] = 10
    arch._user_mech_conv[(user.user_id, "social_proof")] = 6
    # posterior_mean = (1+6)/(2+10) = 7/12 ≈ 0.583

    pen = arch.carryover_penalty(
        user_id=user.user_id,
        mechanism="social_proof",
        week=0,
        hour_of_horizon=5.0,
    )
    import math
    expected_value = 0.5 * (7.0 / 12.0) * math.exp(-5.0 / 10.0)
    assert pen == pytest.approx(expected_value, rel=1e-4)


def test_d_carryover_decays_with_time_gap():
    """Larger Δ → smaller penalty (exponential decay)."""
    arch = FullProposedStack(seed=1)
    config = _config()
    pop = generate_population(config)
    arch.configure(pop)
    user = pop.users[0]

    arch._touch_history[user.user_id].append((0, 0.0, "social_proof"))
    arch._user_mech_n[(user.user_id, "social_proof")] = 5
    arch._user_mech_conv[(user.user_id, "social_proof")] = 3

    pen_recent = arch.carryover_penalty(
        user_id=user.user_id, mechanism="social_proof",
        week=0, hour_of_horizon=1.0,
    )
    pen_distant = arch.carryover_penalty(
        user_id=user.user_id, mechanism="social_proof",
        week=2, hour_of_horizon=0.0,  # 336h later
    )
    assert pen_recent > pen_distant
    assert pen_distant < 1e-4  # ~ exp(-336/24) ≈ 1e-6


# -----------------------------------------------------------------------------
# Shrinkage weight (inherited Spine #4 + Spine #1 mix)
# -----------------------------------------------------------------------------


def test_d_shrinkage_weight_at_zero_n_user():
    arch = FullProposedStack(seed=1)
    config = _config()
    pop = generate_population(config)
    arch.configure(pop)
    user = pop.users[0]
    assert arch.shrinkage_weight(user.user_id, "social_proof") == 0.0


def test_d_shrinkage_weight_at_kappa_is_half():
    arch = FullProposedStack(shrinkage_kappa=10.0, seed=1)
    config = _config()
    pop = generate_population(config)
    arch.configure(pop)
    user = pop.users[0]
    arch._user_mech_n[(user.user_id, "social_proof")] = 10
    assert arch.shrinkage_weight(user.user_id, "social_proof") == pytest.approx(0.5)


# -----------------------------------------------------------------------------
# Cold-start
# -----------------------------------------------------------------------------


def test_d_cold_start_explores_all_cohort_x_mechanism_cells():
    config = _config()
    pop = generate_population(config)
    arch = FullProposedStack(seed=11)
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
# Touch history maintained on record_outcome
# -----------------------------------------------------------------------------


def test_d_record_outcome_updates_touch_history():
    """Spine #2's carryover correction needs touch history; record_outcome
    must populate it."""
    config = _config()
    pop = generate_population(config)
    arch = FullProposedStack(seed=1)
    arch.configure(pop)

    user = pop.users[0]
    assert arch._touch_history.get(user.user_id, []) == []

    arch.record_outcome(Outcome(
        impression_id="i-1", user_id=user.user_id,
        week=0, hour_of_horizon=5.5,
        mechanism_sent="social_proof", converted=True,
    ))
    history = arch._touch_history[user.user_id]
    assert len(history) == 1
    assert history[0] == (0, 5.5, "social_proof")


def test_d_touch_history_bounded_at_100():
    """Memory discipline: touch history capped at 100 entries per user."""
    config = _config()
    pop = generate_population(config)
    arch = FullProposedStack(seed=1)
    arch.configure(pop)

    user = pop.users[0]
    for i in range(150):
        arch.record_outcome(Outcome(
            impression_id=f"i-{i}", user_id=user.user_id,
            week=0, hour_of_horizon=float(i),
            mechanism_sent="social_proof", converted=False,
        ))
    history = arch._touch_history[user.user_id]
    assert len(history) == 100
    # Oldest 50 dropped — newest 100 retained.
    assert history[0][1] == 50.0  # hour_of_horizon of the 51st outcome
    assert history[-1][1] == 149.0


# -----------------------------------------------------------------------------
# Architectural boundary — D vs C
# -----------------------------------------------------------------------------


def test_d_diverges_from_c_when_carryover_matters():
    """Pin C → D architectural boundary. Same population, same
    seed; a config where same-mechanism repetition is plausible
    (high impression rate). D's carryover correction should
    produce different selections than C, which has none."""
    config = _config(
        impression_rate_per_user_per_week=20,  # high → repeats more likely
        seed=999,
    )
    arch_c = TrilateralWithInteraction(seed=42)
    arch_d = FullProposedStack(
        seed=42, carryover_rho=0.8, carryover_tau_hours=12.0,
    )

    result_c = run_single_cell(config, arch_c)
    result_d = run_single_cell(config, arch_d)

    counts_c = result_c.per_mechanism_n
    counts_d = result_d.per_mechanism_n

    assert counts_c != counts_d, (
        "Architectures C and D produced identical selection counts. "
        "D's carryover correction is not differentiating its "
        "selections from C's."
    )


# -----------------------------------------------------------------------------
# Runner end-to-end
# -----------------------------------------------------------------------------


def test_d_runner_round_trip():
    config = _config()
    arch = FullProposedStack(seed=0)
    result = run_single_cell(config, arch)
    assert result.architecture_name == "D_full_proposed_stack"
    assert result.total_impressions > 0


def test_d_runner_deterministic_under_same_seed():
    a = run_single_cell(_config(seed=7), FullProposedStack(seed=7))
    b = run_single_cell(_config(seed=7), FullProposedStack(seed=7))
    assert a.total_impressions == b.total_impressions
    assert a.total_conversions == b.total_conversions
    assert a.per_mechanism_n == b.per_mechanism_n
