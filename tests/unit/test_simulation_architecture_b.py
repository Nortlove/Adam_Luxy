"""Pin Slice 28 — Architecture B (trilateral cascade only, Spine #4).

Per directive Appendix A line 1161 + 2026-05-02 wrap-out scope guard.
Architecture B's scope boundary: trilateral additive scoring (user ×
mechanism × cohort), NO (user × cohort × mechanism) interaction
tensor — that's Architecture C's differentiator.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

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
    TrilateralCascadeOnly,
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
# Protocol + name + interface
# -----------------------------------------------------------------------------


def test_architecture_b_satisfies_protocol():
    arch = TrilateralCascadeOnly()
    assert isinstance(arch, Architecture)


def test_architecture_b_has_canonical_name():
    """Per directive line 1161 the architecture is 'B: trilateral
    cascade only (Spine #4)' — name carries the discriminator."""
    arch = TrilateralCascadeOnly()
    assert arch.name == "B_trilateral_cascade_only"


def test_b_default_weight_split_normalized():
    """Default w_user/w_cohort balanced; both sum to 1 after norm."""
    arch = TrilateralCascadeOnly()
    assert arch.w_user == pytest.approx(0.5)
    assert arch.w_cohort == pytest.approx(0.5)


def test_b_custom_weights_normalize():
    """Custom weights normalize to sum 1."""
    arch = TrilateralCascadeOnly(w_user=2.0, w_cohort=1.0)
    assert arch.w_user + arch.w_cohort == pytest.approx(1.0)
    assert arch.w_user > arch.w_cohort


def test_b_zero_weights_raises():
    with pytest.raises(ValueError):
        TrilateralCascadeOnly(w_user=0.0, w_cohort=0.0)


# -----------------------------------------------------------------------------
# Configure
# -----------------------------------------------------------------------------


def test_b_configure_records_user_cohort_mapping():
    """configure must capture user→cohort so context-conditioning works."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralCascadeOnly(seed=1)
    arch.configure(pop)
    # Every population user should be in the mapping.
    for u in pop.users:
        assert arch._user_cohort.get(u.user_id) == u.cohort_id


def test_b_configure_resets_state():
    """Re-configuring a single instance must reset accumulator state
    (no leakage across cells)."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralCascadeOnly(seed=1)
    arch.configure(pop)

    # Inject some accumulator state.
    arch._user_mech_n[("u-fake", "m-fake")] = 100
    arch._cohort_mech_conv[(99, "m-fake")] = 50

    arch.configure(pop)  # reset
    assert arch._user_mech_n.get(("u-fake", "m-fake"), 0) == 0
    assert arch._cohort_mech_conv.get((99, "m-fake"), 0) == 0


# -----------------------------------------------------------------------------
# Cold-start exploration
# -----------------------------------------------------------------------------


def test_b_cold_start_explores_all_cohort_x_mechanism_cells():
    """Until each (cohort, mechanism) cell has ≥1 observation, B
    selects only from untried cells. Trilateral cascade is
    cohort-aware, so cold-start is per-cohort."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralCascadeOnly(seed=11)
    arch.configure(pop)

    # Pick one user per cohort.
    by_cohort = pop.by_cohort()
    user_per_cohort = {c: us[0] for c, us in by_cohort.items()}

    # For each cohort, run len(mechanisms) impressions; verify
    # every mechanism gets touched at least once.
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
        # Cold-start must have visited every mechanism for this cohort.
        assert seen == set(pop.mechanisms)


# -----------------------------------------------------------------------------
# Trilateral scoring — user + cohort signals both consumed
# -----------------------------------------------------------------------------


def test_b_score_uses_both_user_and_cohort_rates():
    """Verify _trilateral_score combines both components per the
    weighted average. Inject deterministic stats and check the
    score equals the expected weighted sum."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralCascadeOnly(w_user=0.5, w_cohort=0.5, seed=1)
    arch.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]
    cohort = user.cohort_id

    # Inject: user has 4 conversions out of 10 → user rate = 5/12 (Laplace).
    arch._user_mech_n[(user.user_id, mech)] = 10
    arch._user_mech_conv[(user.user_id, mech)] = 4
    # Cohort has 6 conversions out of 20 → cohort rate = 7/22.
    arch._cohort_mech_n[(cohort, mech)] = 20
    arch._cohort_mech_conv[(cohort, mech)] = 6

    expected_user = (1 + 4) / float(2 + 10)
    expected_cohort = (1 + 6) / float(2 + 20)
    expected_score = 0.5 * expected_user + 0.5 * expected_cohort
    actual_score = arch._trilateral_score(user.user_id, mech)
    assert actual_score == pytest.approx(expected_score)


def test_b_score_uses_user_weight_only_when_w_cohort_zero():
    """When w_cohort=0, the score collapses to user signal."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralCascadeOnly(w_user=1.0, w_cohort=0.001, seed=1)
    arch.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]
    arch._user_mech_n[(user.user_id, mech)] = 5
    arch._user_mech_conv[(user.user_id, mech)] = 2

    score = arch._trilateral_score(user.user_id, mech)
    expected_user_rate = 3.0 / 7.0
    assert score == pytest.approx(expected_user_rate, abs=0.01)


def test_b_no_interaction_term():
    """Sanity: B's score is ADDITIVE in user + cohort components.
    There is no per-(user × cohort × mechanism) interaction cell.
    Architecture C will introduce this; B does not."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralCascadeOnly(seed=1)
    arch.configure(pop)

    # Two users in the SAME cohort.
    cohort_users = pop.by_cohort()[0]
    if len(cohort_users) < 2:
        pytest.skip("need at least 2 users in cohort 0")
    u1, u2 = cohort_users[0], cohort_users[1]
    mech = pop.mechanisms[0]

    # Identical user-side stats; cohort-side stats are identical
    # by construction (same cohort).
    for u in (u1, u2):
        arch._user_mech_n[(u.user_id, mech)] = 5
        arch._user_mech_conv[(u.user_id, mech)] = 2
    arch._cohort_mech_n[(0, mech)] = 50
    arch._cohort_mech_conv[(0, mech)] = 20

    s1 = arch._trilateral_score(u1.user_id, mech)
    s2 = arch._trilateral_score(u2.user_id, mech)
    # Without interaction, identical user-side stats + identical
    # cohort = identical scores. (An interaction-aware architecture
    # could differentiate via per-user × cohort cell.)
    assert s1 == pytest.approx(s2)


# -----------------------------------------------------------------------------
# record_outcome updates all stat tiers
# -----------------------------------------------------------------------------


def test_b_record_outcome_increments_user_and_cohort_stats():
    """A single outcome must update both user-level AND cohort-level
    accumulators — both are inputs to the trilateral score."""
    config = _config()
    pop = generate_population(config)
    arch = TrilateralCascadeOnly(seed=1)
    arch.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]
    cohort = user.cohort_id

    # Pre: zeros.
    assert arch._user_mech_n[(user.user_id, mech)] == 0
    assert arch._cohort_mech_n[(cohort, mech)] == 0

    arch.record_outcome(Outcome(
        impression_id="i", user_id=user.user_id,
        week=0, hour_of_horizon=0.0,
        mechanism_sent=mech, converted=True,
    ))

    assert arch._user_mech_n[(user.user_id, mech)] == 1
    assert arch._user_mech_conv[(user.user_id, mech)] == 1
    assert arch._cohort_mech_n[(cohort, mech)] == 1
    assert arch._cohort_mech_conv[(cohort, mech)] == 1


def test_b_record_outcome_non_conversion_increments_n_only():
    config = _config()
    pop = generate_population(config)
    arch = TrilateralCascadeOnly(seed=1)
    arch.configure(pop)

    user = pop.users[0]
    mech = pop.mechanisms[0]
    cohort = user.cohort_id

    arch.record_outcome(Outcome(
        impression_id="i", user_id=user.user_id,
        week=0, hour_of_horizon=0.0,
        mechanism_sent=mech, converted=False,
    ))
    assert arch._user_mech_n[(user.user_id, mech)] == 1
    assert arch._user_mech_conv[(user.user_id, mech)] == 0
    assert arch._cohort_mech_n[(cohort, mech)] == 1
    assert arch._cohort_mech_conv[(cohort, mech)] == 0


# -----------------------------------------------------------------------------
# Runner end-to-end
# -----------------------------------------------------------------------------


def test_b_runner_round_trip():
    config = _config()
    arch = TrilateralCascadeOnly(seed=0)
    result = run_single_cell(config, arch)
    assert result.architecture_name == "B_trilateral_cascade_only"
    assert result.total_impressions > 0
    expected = (
        config.audience_size_per_cohort
        * config.n_cohorts
        * config.impression_rate_per_user_per_week
        * config.horizon_weeks
    )
    assert result.total_impressions == expected
    # Per-mechanism counts sum to the totals.
    assert sum(result.per_mechanism_n.values()) == result.total_impressions
    assert (
        sum(result.per_mechanism_conversions.values())
        == result.total_conversions
    )


def test_b_runner_deterministic_under_same_seed():
    arch_a = TrilateralCascadeOnly(seed=7)
    a = run_single_cell(_config(seed=7), arch_a)

    arch_b = TrilateralCascadeOnly(seed=7)
    b = run_single_cell(_config(seed=7), arch_b)

    assert a.total_impressions == b.total_impressions
    assert a.total_conversions == b.total_conversions
    assert a.per_mechanism_n == b.per_mechanism_n


# -----------------------------------------------------------------------------
# B exploits cohort-separated structure that A cannot
# -----------------------------------------------------------------------------


def test_b_exploits_cohort_separation_better_than_a_on_strong_separable():
    """On a strongly-cohort-separable config, Architecture B's
    per-cohort scoring should produce a measurably different action
    distribution than Architecture A's per-mechanism-only baseline.

    Pin: with the same seed, A and B should NOT produce identical
    selections — B's cohort-aware scoring uses signal A is blind to.

    (Lift comparison is the simulation's job; this test pins only
    that B's scoring DOES use the cohort signal differently from A.)
    """
    config = _config(
        cohort_separation=CohortSeparation.STRONGLY_SEPARABLE,
        interaction_strength=InteractionStrength.NONE,  # isolate
                                                         # cohort effect
        audience_size_per_cohort=20,
        impression_rate_per_user_per_week=7,
        horizon_weeks=2,
        seed=999,
    )
    arch_a = MarginalAdditiveBaseline(seed=42)
    arch_b = TrilateralCascadeOnly(seed=42, w_user=0.0, w_cohort=1.0)

    result_a = run_single_cell(config, arch_a)
    result_b = run_single_cell(config, arch_b)

    # Selection distributions: counts per mechanism.
    counts_a = result_a.per_mechanism_n
    counts_b = result_b.per_mechanism_n

    # The two distributions should NOT be identical — B's cohort
    # signal causes a different selection pattern over the same
    # impression stream. (Stochastic noise alone wouldn't reliably
    # flip distributions; cohort-aware scoring will.)
    assert counts_a != counts_b, (
        f"Architectures A and B produced identical selection "
        f"counts: {counts_a}. B's cohort-aware scoring is not "
        "actually being consulted, OR the cohort signal is too weak "
        "to differentiate."
    )
