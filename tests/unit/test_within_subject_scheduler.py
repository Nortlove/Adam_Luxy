"""Pin Spine #2 — within-subject schedule generators (ABAB / RAR / SMART)
and the mechanism washout table. Directive Phase 1 line 948-950.

The AR(1) carryover correction (line 951) is pinned by
test_user_posterior_hmc_reconcile.py; this file pins the SCHEDULER side.
"""

from __future__ import annotations

import json
import random

import pytest

from adam.intelligence.mechanism_adme import MECHANISM_PROFILES
from adam.retargeting.models.within_subject import (
    UserMechanismPosterior,
    UserPosteriorProfile,
    WithinSubjectDesign,
)
from adam.retargeting.scheduler import (
    DEFAULT_WASHOUT_HOURS,
    RAR_MIN_ARM_PROBABILITY,
    SMART_RESPONDER_REWARD_THRESHOLD,
    SMART_STAGE_2_TRIGGER_POSITION,
    WASHOUT_HALF_LIFE_MULTIPLIER,
    build_washout_table,
    design_abab,
    design_rar,
    design_smart,
    rar_arm_probabilities,
    rar_sample_mechanism,
    smart_stage_2_assignment,
    washout_hours_between,
    washout_hours_for,
)


# -----------------------------------------------------------------------------
# Washout table
# -----------------------------------------------------------------------------


def test_washout_constants_canonical():
    """Pin the multiplier — three half-lives is ≥87.5% washout
    (first-order PK). Change forces explicit recalibration."""
    assert WASHOUT_HALF_LIFE_MULTIPLIER == 3.0
    assert DEFAULT_WASHOUT_HOURS == 144.0


def test_washout_for_known_mechanisms():
    """Each ADME profile half-life × 3 must round-trip through
    washout_hours_for. Pins the contract that washout reads from
    the canonical ADME table — no hidden duplication."""
    for mech, profile in MECHANISM_PROFILES.items():
        assert washout_hours_for(mech) == profile.half_life_hours * 3.0


def test_washout_for_unknown_mechanism_uses_default():
    """Unknown mechanism falls through to the safe default — protects
    against zero-washout for experimental / new mechanisms."""
    assert washout_hours_for("nonexistent_mech_xyz") == DEFAULT_WASHOUT_HOURS


def test_washout_between_takes_max():
    """Cross-mechanism transition uses MAX of both washouts —
    slower-clearing mechanism dominates."""
    # scarcity = 4h × 3 = 12h, authority = 240h × 3 = 720h
    assert washout_hours_between("scarcity", "authority") == 720.0
    assert washout_hours_between("authority", "scarcity") == 720.0
    # Same mechanism reduces to washout_hours_for
    assert washout_hours_between("scarcity", "scarcity") == 12.0


def test_build_washout_table_contains_all_mechanisms():
    """Snapshot covers every ADME-profiled mechanism."""
    table = build_washout_table()
    for mech in MECHANISM_PROFILES.keys():
        assert mech in table
        assert table[mech] > 0.0


# -----------------------------------------------------------------------------
# ABAB
# -----------------------------------------------------------------------------


def test_abab_alternates_correctly():
    """Even index → A, odd index → B for max_touches positions."""
    design = design_abab(
        user_id="u1",
        sequence_id="s1",
        mechanism_a="authority",
        mechanism_b="social_proof",
        max_touches=7,
    )
    assert design.design_type == "ABAB"
    assert design.abab_pattern == [
        "authority", "social_proof", "authority", "social_proof",
        "authority", "social_proof", "authority",
    ]
    assert design.abab_a == "authority"
    assert design.abab_b == "social_proof"


def test_abab_washout_floor_per_transition():
    """Each transition floor = max(washout_a, washout_b).
    For authority↔social_proof: max(720, 216) = 720h every time."""
    design = design_abab("u", "s", "authority", "social_proof", max_touches=4)
    expected = max(
        washout_hours_for("authority"),
        washout_hours_for("social_proof"),
    )
    assert design.washout_hours_between_touches == [expected, expected, expected]


def test_abab_every_position_is_exploration():
    """ABAB has no pure exploit slots — every position is a
    comparison observation."""
    design = design_abab("u", "s", "authority", "social_proof", max_touches=4)
    assert design.exploration_slots == [1, 2, 3, 4]
    assert design.exploitation_slots == []


def test_abab_rejects_identical_mechanisms():
    with pytest.raises(ValueError):
        design_abab("u", "s", "authority", "authority", max_touches=4)


def test_abab_rejects_too_few_touches():
    with pytest.raises(ValueError):
        design_abab("u", "s", "authority", "social_proof", max_touches=1)


def test_abab_roundtrips_through_json():
    """The ABAB pattern + washout floor MUST survive serialization
    (sequences are persisted to Redis as JSON)."""
    design = design_abab("u", "s", "authority", "social_proof", max_touches=5)
    payload = json.loads(design.model_dump_json())
    assert payload["abab_pattern"] == design.abab_pattern
    assert payload["washout_hours_between_touches"] == design.washout_hours_between_touches
    assert payload["abab_a"] == "authority"
    assert payload["abab_b"] == "social_proof"
    # And reconstitutes
    rebuilt = WithinSubjectDesign(**payload)
    assert rebuilt.abab_pattern == design.abab_pattern


# -----------------------------------------------------------------------------
# RAR
# -----------------------------------------------------------------------------


def test_rar_constants_canonical():
    assert RAR_MIN_ARM_PROBABILITY == 0.10


def test_rar_uniform_when_no_priors_and_no_user():
    """With no user profile and no population means, the distribution
    is uniform over candidates."""
    probs = rar_arm_probabilities(["authority", "social_proof", "scarcity"])
    # Uniform weights → all equal after floor mixing
    assert pytest.approx(probs["authority"], abs=1e-9) == probs["social_proof"]
    assert pytest.approx(probs["authority"], abs=1e-9) == probs["scarcity"]
    assert pytest.approx(sum(probs.values()), abs=1e-9) == 1.0


def test_rar_proportional_to_population_means():
    """When population_means differ, probabilities are proportional
    to mean (after the uniform floor)."""
    probs = rar_arm_probabilities(
        ["authority", "social_proof"],
        population_means={"authority": 0.8, "social_proof": 0.2},
    )
    # Authority has 4x the population mean, so authority > social_proof
    assert probs["authority"] > probs["social_proof"]
    assert pytest.approx(sum(probs.values()), abs=1e-9) == 1.0


def test_rar_min_arm_probability_floor_holds():
    """No arm should ever drop below the minimum allocation — protects
    against bandit killing an arm prematurely."""
    probs = rar_arm_probabilities(
        ["authority", "social_proof"],
        # Pathological: zero population mean for social_proof
        population_means={"authority": 0.99, "social_proof": 0.0},
    )
    assert probs["social_proof"] >= RAR_MIN_ARM_PROBABILITY - 1e-9


def test_rar_user_posterior_overrides_population():
    """User-level mean (with observations) overrides population mean."""
    profile = UserPosteriorProfile(
        user_id="u", brand_id="b", archetype_id="a",
    )
    # User has tried authority with 12 hits → α=14, β=2, mean = 14/16 = 0.875
    user_post = UserMechanismPosterior(user_id="u", mechanism="authority")
    for _ in range(12):
        user_post.update(1.0)
    profile.mechanism_posteriors["authority"] = user_post

    probs_with_user = rar_arm_probabilities(
        ["authority", "social_proof"],
        user_profile=profile,
        # Population says authority is weak
        population_means={"authority": 0.1, "social_proof": 0.5},
    )
    probs_pop_only = rar_arm_probabilities(
        ["authority", "social_proof"],
        population_means={"authority": 0.1, "social_proof": 0.5},
    )
    # User-level signal STRONGLY favors authority (mean 0.875) — must
    # weight authority MORE than the population-only baseline does.
    assert probs_with_user["authority"] > probs_pop_only["authority"]


def test_rar_sample_returns_member_of_candidates():
    rng = random.Random(42)
    chosen, probs = rar_sample_mechanism(
        ["authority", "social_proof", "scarcity"],
        rng=rng,
    )
    assert chosen in {"authority", "social_proof", "scarcity"}
    assert pytest.approx(sum(probs.values()), abs=1e-9) == 1.0


def test_rar_sample_distribution_concentrates_on_high_mean_arm():
    """With 1000 draws and mean(A)=0.9 vs mean(B)=0.1, A should be
    chosen more often than B — empirical validation of the
    bandit weighting."""
    rng = random.Random(7)
    chosen_count = {"a": 0, "b": 0}
    for _ in range(1000):
        chosen, _ = rar_sample_mechanism(
            ["a", "b"],
            population_means={"a": 0.9, "b": 0.1},
            rng=rng,
        )
        chosen_count[chosen] += 1
    assert chosen_count["a"] > chosen_count["b"]
    # Still respects floor — neither arm goes to zero
    assert chosen_count["b"] > 50  # ≥10% floor across 1000 draws


def test_rar_design_pattern_length_matches_max_touches():
    rng = random.Random(0)
    design = design_rar(
        user_id="u",
        sequence_id="s",
        candidates=["authority", "social_proof"],
        max_touches=5,
        rng=rng,
    )
    assert design.design_type == "RAR"
    assert len(design.rar_pattern) == 5
    assert len(design.rar_per_touch_probabilities) == 5
    assert len(design.washout_hours_between_touches) == 4
    for probs in design.rar_per_touch_probabilities:
        assert pytest.approx(sum(probs.values()), abs=1e-9) == 1.0


def test_rar_design_roundtrips_through_json():
    rng = random.Random(0)
    design = design_rar(
        user_id="u", sequence_id="s",
        candidates=["authority", "social_proof"],
        max_touches=3, rng=rng,
    )
    payload = json.loads(design.model_dump_json())
    assert payload["rar_pattern"] == design.rar_pattern
    assert payload["rar_candidates"] == ["authority", "social_proof"]
    rebuilt = WithinSubjectDesign(**payload)
    assert rebuilt.rar_pattern == design.rar_pattern


def test_rar_rejects_empty_candidates():
    with pytest.raises(ValueError):
        design_rar("u", "s", [], max_touches=3)


# -----------------------------------------------------------------------------
# SMART
# -----------------------------------------------------------------------------


def test_smart_constants_canonical():
    """Threshold and trigger position pinned — change forces
    explicit recalibration of the responder rule."""
    assert SMART_RESPONDER_REWARD_THRESHOLD == 0.4
    assert SMART_STAGE_2_TRIGGER_POSITION == 3


def test_smart_pre_trigger_uses_stage_1():
    """Pre-trigger positions ALL deploy stage_1_mechanism — branching
    only happens at trigger."""
    design = design_smart(
        user_id="u", sequence_id="s",
        stage_1_mechanism="authority",
        rescue_mechanism="social_proof",
        max_touches=7, trigger_position=3,
    )
    # Both responder and non-responder branches share positions 1..3
    assert design.smart_pattern_responder[:3] == ["authority", "authority", "authority"]
    assert design.smart_pattern_non_responder[:3] == ["authority", "authority", "authority"]


def test_smart_responder_branch_continues_stage_1():
    """Responder branch: keep stage_1 mechanism for remaining positions."""
    design = design_smart(
        user_id="u", sequence_id="s",
        stage_1_mechanism="authority",
        rescue_mechanism="social_proof",
        max_touches=5, trigger_position=2,
    )
    assert design.smart_pattern_responder == ["authority"] * 5


def test_smart_non_responder_branch_switches_to_rescue():
    """Non-responder branch: switch to rescue mechanism after trigger."""
    design = design_smart(
        user_id="u", sequence_id="s",
        stage_1_mechanism="authority",
        rescue_mechanism="social_proof",
        max_touches=5, trigger_position=2,
    )
    assert design.smart_pattern_non_responder == [
        "authority", "authority", "social_proof", "social_proof", "social_proof"
    ]


def test_smart_decision_rule_branches_on_threshold():
    design = design_smart(
        user_id="u", sequence_id="s",
        stage_1_mechanism="authority",
        rescue_mechanism="social_proof",
        max_touches=5, trigger_position=2,
        responder_threshold=0.4,
    )
    # Above threshold → responder
    mech, label = smart_stage_2_assignment(design, cumulative_reward=0.6)
    assert mech == "authority"
    assert label == "responder_continue"
    # Below threshold → switch
    mech, label = smart_stage_2_assignment(design, cumulative_reward=0.1)
    assert mech == "social_proof"
    assert label == "non_responder_switch"
    # Exactly at threshold → responder (>=)
    mech, label = smart_stage_2_assignment(design, cumulative_reward=0.4)
    assert mech == "authority"
    assert label == "responder_continue"


def test_smart_washout_floors_per_branch():
    """Both responder and non-responder washout sequences are populated."""
    design = design_smart(
        user_id="u", sequence_id="s",
        stage_1_mechanism="authority",
        rescue_mechanism="social_proof",
        max_touches=4, trigger_position=2,
    )
    assert len(design.smart_washout_responder) == 3
    assert len(design.smart_washout_non_responder) == 3
    # Responder branch is all-authority → all transitions = 720h
    auth_w = washout_hours_for("authority")
    assert design.smart_washout_responder == [auth_w, auth_w, auth_w]
    # Non-responder switches at position 3 — that transition uses MAX
    # (which is authority, the slower one)
    assert design.smart_washout_non_responder[1] == max(
        washout_hours_for("authority"),
        washout_hours_for("social_proof"),
    )


def test_smart_rejects_identical_mechanisms():
    with pytest.raises(ValueError):
        design_smart(
            "u", "s", "authority", "authority", max_touches=5, trigger_position=2,
        )


def test_smart_rejects_invalid_trigger_position():
    """trigger_position must leave at least 1 post-trigger position."""
    with pytest.raises(ValueError):
        design_smart(
            "u", "s", "authority", "social_proof",
            max_touches=5, trigger_position=5,  # No room for stage 2
        )
    with pytest.raises(ValueError):
        design_smart(
            "u", "s", "authority", "social_proof",
            max_touches=5, trigger_position=0,  # Must be >= 1
        )


def test_smart_design_roundtrips_through_json():
    design = design_smart(
        user_id="u", sequence_id="s",
        stage_1_mechanism="authority",
        rescue_mechanism="social_proof",
        max_touches=5, trigger_position=2,
    )
    payload = json.loads(design.model_dump_json())
    rebuilt = WithinSubjectDesign(**payload)
    assert rebuilt.smart_stage_1_mechanism == "authority"
    assert rebuilt.smart_rescue_mechanism == "social_proof"
    assert rebuilt.smart_trigger_position == 2
    assert rebuilt.smart_pattern_responder == design.smart_pattern_responder
    assert rebuilt.smart_pattern_non_responder == design.smart_pattern_non_responder
    # And the decision rule still works on the rebuilt design
    mech, label = smart_stage_2_assignment(rebuilt, cumulative_reward=0.6)
    assert mech == "authority"
    assert label == "responder_continue"
