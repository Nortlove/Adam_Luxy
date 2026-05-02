"""Pin Slice 31 — Architecture E (full stack + counterfactual logging).

Per directive Appendix A line 1164. E inherits D's selection logic
+ adds Spine #6 propensity logging (per-decision propensity_log
entries + effective_sample_size diagnostic).
"""

from __future__ import annotations

import pytest

from adam.intelligence.simulation import (
    Architecture,
    CohortSeparation,
    FullProposedStack,
    FullStackPlusCounterfactual,
    Impression,
    InteractionStrength,
    NonStationarityRegime,
    Outcome,
    SimulationConfig,
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


def test_architecture_e_satisfies_protocol():
    arch = FullStackPlusCounterfactual()
    assert isinstance(arch, Architecture)


def test_architecture_e_has_canonical_name():
    arch = FullStackPlusCounterfactual()
    assert arch.name == "E_full_stack_plus_counterfactual"


def test_e_default_propensity_mc_samples():
    arch = FullStackPlusCounterfactual()
    assert arch.propensity_mc_samples == 50


def test_e_default_ips_clip():
    arch = FullStackPlusCounterfactual()
    assert arch.ips_clip == 0.01


def test_e_zero_mc_samples_raises():
    with pytest.raises(ValueError):
        FullStackPlusCounterfactual(propensity_mc_samples=0)


def test_e_invalid_ips_clip_raises():
    with pytest.raises(ValueError):
        FullStackPlusCounterfactual(ips_clip=0.0)
    with pytest.raises(ValueError):
        FullStackPlusCounterfactual(ips_clip=1.0)
    with pytest.raises(ValueError):
        FullStackPlusCounterfactual(ips_clip=-0.5)


# -----------------------------------------------------------------------------
# Propensity logging — Spine #6's contribution
# -----------------------------------------------------------------------------


def test_e_logs_one_entry_per_select():
    """Every select_mechanism call must append exactly one
    propensity_log entry."""
    config = _config()
    pop = generate_population(config)
    arch = FullStackPlusCounterfactual(seed=11)
    arch.configure(pop)

    user = pop.users[0]
    n_calls = 5
    for i in range(n_calls):
        imp = Impression(
            impression_id=f"i-{i}", user_id=user.user_id,
            week=0, hour_of_horizon=float(i),
        )
        arch.select_mechanism(imp)

    log = arch.propensity_log
    assert len(log) == n_calls
    for i, entry in enumerate(log):
        assert entry["impression_id"] == f"i-{i}"
        assert entry["user_id"] == user.user_id


def test_e_log_entry_carries_propensity_and_distribution():
    """Each log entry must have p_t in (0, 1] AND all_propensities
    summing to 1 (policy distribution)."""
    config = _config()
    pop = generate_population(config)
    arch = FullStackPlusCounterfactual(seed=11)
    arch.configure(pop)

    # Cold-start exploration produces deterministic propensities;
    # use a warm-state user so the Thompson distribution is non-trivial.
    user = pop.users[0]
    for m in pop.mechanisms:
        arch._inner._cohort_mech_n[(user.cohort_id, m)] = 50
        arch._inner._cohort_mech_conv[(user.cohort_id, m)] = 25

    imp = Impression(
        impression_id="i-warm", user_id=user.user_id,
        week=0, hour_of_horizon=10.0,
    )
    arch.select_mechanism(imp)

    entry = arch.propensity_log[-1]
    assert 0.0 < entry["p_t"] <= 1.0
    # All_propensities sum to 1 (Monte Carlo discrete distribution).
    total = sum(entry["all_propensities"].values())
    assert total == pytest.approx(1.0)


def test_e_record_outcome_tags_log_with_reward():
    """When an outcome arrives, the matching log entry's reward
    field is populated."""
    config = _config()
    pop = generate_population(config)
    arch = FullStackPlusCounterfactual(seed=11)
    arch.configure(pop)

    user = pop.users[0]
    imp = Impression(
        impression_id="i-1", user_id=user.user_id,
        week=0, hour_of_horizon=0.0,
    )
    chosen = arch.select_mechanism(imp)
    arch.record_outcome(Outcome(
        impression_id="i-1", user_id=user.user_id,
        week=0, hour_of_horizon=0.0,
        mechanism_sent=chosen, converted=True,
    ))
    log = arch.propensity_log
    assert len(log) == 1
    assert log[0]["reward"] == 1


def test_e_record_outcome_unmatched_impression_id_no_crash():
    """An outcome whose impression_id isn't in the log doesn't crash;
    it's a no-op for tagging (but still updates inner accumulators)."""
    config = _config()
    pop = generate_population(config)
    arch = FullStackPlusCounterfactual(seed=11)
    arch.configure(pop)

    user = pop.users[0]
    arch.record_outcome(Outcome(
        impression_id="never-saw-this", user_id=user.user_id,
        week=0, hour_of_horizon=0.0,
        mechanism_sent="social_proof", converted=True,
    ))
    # No exceptions raised.


# -----------------------------------------------------------------------------
# Effective Sample Size diagnostic
# -----------------------------------------------------------------------------


def test_e_ess_zero_when_no_log():
    arch = FullStackPlusCounterfactual(seed=1)
    assert arch.effective_sample_size() == 0.0


def test_e_ess_equals_n_when_propensities_uniform():
    """When all p_t are identical (uniform policy), IPS ESS equals
    the raw count — no variance amplification."""
    config = _config()
    pop = generate_population(config)
    arch = FullStackPlusCounterfactual(seed=11)
    arch.configure(pop)

    # Manually inject 10 log entries with identical p_t.
    for i in range(10):
        arch._propensity_log.append({
            "impression_id": f"manual-{i}",
            "user_id": "u",
            "mechanism_chosen": "social_proof",
            "p_t": 0.5,
            "all_propensities": {},
            "reward": 1,
        })
    ess = arch.effective_sample_size()
    assert ess == pytest.approx(10.0, abs=0.01)


def test_e_ess_less_than_n_when_propensities_variable():
    """Variable p_t → ESS < N (the IPS variance penalty)."""
    arch = FullStackPlusCounterfactual(seed=1)
    # Inject 10 entries with HIGHLY variable p_t — the IPS weights
    # are wildly imbalanced, so ESS << 10.
    for i in range(10):
        p_t = 0.9 if i == 0 else 0.05  # one dominant + 9 long-tail
        arch._propensity_log.append({
            "impression_id": f"manual-{i}",
            "user_id": "u",
            "mechanism_chosen": "social_proof",
            "p_t": p_t,
            "all_propensities": {},
            "reward": 0,
        })
    ess = arch.effective_sample_size()
    assert ess < 10.0
    assert ess > 0.0


# -----------------------------------------------------------------------------
# E vs D — selection equivalence (Spine #6 doesn't disturb the policy)
# -----------------------------------------------------------------------------


def test_e_logging_does_not_disturb_inner_selections():
    """The pin: Spine #6 enables OPE WITHOUT changing the
    production policy's selections. With the same seed parity,
    E's chosen mechanisms over an impression stream should match
    what the inner FullProposedStack would have chosen alone.

    Note: E's MC-propensity estimation uses a separate _mc_rng
    seeded from main_seed + 31337, so it doesn't disturb the
    inner Thompson sampling RNG state.
    """
    config = _config()

    # Run E end-to-end.
    arch_e = FullStackPlusCounterfactual(seed=7)
    result_e = run_single_cell(config, arch_e)

    # Run a stand-alone FullProposedStack with the SAME seed.
    arch_d = FullProposedStack(seed=7)
    result_d = run_single_cell(config, arch_d)

    # Per-mechanism counts identical → selection sequence identical
    # (deterministic from seed in both runs).
    assert result_e.per_mechanism_n == result_d.per_mechanism_n


# -----------------------------------------------------------------------------
# Runner end-to-end
# -----------------------------------------------------------------------------


def test_e_runner_round_trip():
    config = _config()
    arch = FullStackPlusCounterfactual(seed=0)
    result = run_single_cell(config, arch)
    assert result.architecture_name == "E_full_stack_plus_counterfactual"
    assert result.total_impressions > 0
    # After the run, the propensity log carries one entry per impression.
    assert len(arch.propensity_log) == result.total_impressions


def test_e_runner_deterministic_under_same_seed():
    a = run_single_cell(_config(seed=7), FullStackPlusCounterfactual(seed=7))
    b = run_single_cell(_config(seed=7), FullStackPlusCounterfactual(seed=7))
    assert a.total_impressions == b.total_impressions
    assert a.total_conversions == b.total_conversions
    assert a.per_mechanism_n == b.per_mechanism_n
