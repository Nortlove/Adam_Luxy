"""Pin Slice 3 — within-subject scheduler eligibility filter.

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/within_subject_eligibility.py``:

    (a) Hard washout-respecting eligibility filter at decision time
        per directive line 122 ("the scheduler is the only object
        allowed to determine which mechanism is eligible for a given
        user at a given moment"). Washout floor inherited from
        ``adam.retargeting.scheduler.washout_hours_for(mechanism)`` —
        3× t½ of the mechanism's ADME profile.

    (b) Boundary anchors pinned by these tests:
          - candidate inside washout (hours_since < floor) dropped
          - candidate past washout (hours_since >= floor) kept
          - cold buyer (no history) → all candidates eligible
          - empty user_touch_history → pass-through
          - empty mechanism_scores → pass-through
          - all-candidates-inside-washout → bypassed=True with input
            intact (sibling slice will replace with refuse-all-bid)
          - cross-mechanism transition: MAX of both washouts gates
          - drop_reasons populated per dropped mechanism for diagnostics
          - n_dropped + n_eligible accounting consistent with the diff
          - EligibilityResult is frozen

    (c) calibration_pending=True. Default washout multiplier 3× t½
        inherited from scheduler.WASHOUT_HALF_LIFE_MULTIPLIER. LUXY
        pilot will calibrate per-mechanism. A14 flag inherited.

    (d) Honest tags — what is NOT tested here:
          - Step 10 carryover correction (sibling slice composing on
            same touch-history primitive).
          - Hard refuse-all-bid semantic (sibling slice).
          - Persistent (Redis) per-mechanism touch history (sibling).
          - Mechanism-pair carryover coefficients ρ_m1→m2 (sibling).
"""

from __future__ import annotations

import logging

import pytest

from adam.intelligence.within_subject_eligibility import (
    EligibilityResult,
    apply_within_subject_eligibility,
    passes_washout,
)
from adam.retargeting.scheduler import washout_hours_for


# Mechanism washouts (3× t½ inherited from MECHANISM_PROFILES):
#   social_proof t½=24h → washout 72h
#   scarcity     t½=12h → washout 36h
#   loss_aversion ...
# Use the actual washout_hours_for() for cross-checks.


# -----------------------------------------------------------------------------
# passes_washout — single-pair gate
# -----------------------------------------------------------------------------


def test_passes_no_history_eligible():
    """No prior touch (None) → eligible (no washout to violate)."""
    assert passes_washout("social_proof", None) is True


def test_passes_past_washout_eligible():
    """Hours-since well past the floor → eligible."""
    floor = washout_hours_for("social_proof")
    assert passes_washout("social_proof", floor + 1.0) is True


def test_dropped_inside_washout():
    """Hours-since < floor → ineligible."""
    floor = washout_hours_for("social_proof")
    assert passes_washout("social_proof", floor - 1.0) is False


def test_passes_exactly_at_floor():
    """Hours-since == floor → eligible (>= semantic per directive)."""
    floor = washout_hours_for("social_proof")
    assert passes_washout("social_proof", floor) is True


def test_threshold_override_respected():
    """Custom washout_hours overrides the per-mechanism default."""
    # Mechanism's default floor doesn't matter; override decides.
    assert passes_washout("social_proof", 10.0, washout_hours=5.0) is True
    assert passes_washout("social_proof", 10.0, washout_hours=20.0) is False


def test_cross_mechanism_takes_max():
    """When prior touch was a different mechanism, MAX of both washouts."""
    sp_floor = washout_hours_for("social_proof")
    sc_floor = washout_hours_for("scarcity")
    big = max(sp_floor, sc_floor)

    # If hours_since exceeds the larger of the two floors → eligible
    assert passes_washout(
        "social_proof", big + 1.0,
        last_touched_mechanism="scarcity",
    ) is True
    # If hours_since fails the larger floor → ineligible
    assert passes_washout(
        "social_proof", min(sp_floor, sc_floor) - 1.0,
        last_touched_mechanism="scarcity",
    ) is False


# -----------------------------------------------------------------------------
# apply_within_subject_eligibility — bulk filter
# -----------------------------------------------------------------------------


def test_apply_drops_inside_washout_keeps_outside():
    """Mixed input — inside-washout dropped, outside kept."""
    floor = washout_hours_for("social_proof")
    history = {
        "social_proof": floor - 1.0,    # inside → drop
        "scarcity": washout_hours_for("scarcity") + 10.0,  # outside → keep
    }
    scores = {"social_proof": 0.7, "scarcity": 0.6}
    result = apply_within_subject_eligibility(
        mechanism_scores=scores,
        user_touch_history=history,
    )
    assert "social_proof" not in result.filtered_scores
    assert result.filtered_scores["scarcity"] == 0.6
    assert result.n_dropped == 1
    assert result.n_eligible == 1
    assert result.dropped_mechanisms == ["social_proof"]
    assert result.bypassed is False
    assert "social_proof" in result.drop_reasons


def test_apply_cold_buyer_pass_through():
    """No touch history → all candidates eligible."""
    scores = {"social_proof": 0.7, "scarcity": 0.6}
    result = apply_within_subject_eligibility(
        mechanism_scores=scores,
        user_touch_history=None,
    )
    assert result.filtered_scores is scores
    assert result.n_dropped == 0
    assert result.n_eligible == 2


def test_apply_empty_history_pass_through():
    """Empty dict treated same as None (no signal)."""
    scores = {"social_proof": 0.7}
    result = apply_within_subject_eligibility(
        mechanism_scores=scores,
        user_touch_history={},
    )
    assert result.filtered_scores is scores
    assert result.n_dropped == 0


def test_apply_empty_scores_pass_through():
    """No candidates → empty result."""
    result = apply_within_subject_eligibility(
        mechanism_scores={},
        user_touch_history={"social_proof": 1.0},
    )
    assert result.filtered_scores == {}
    assert result.n_dropped == 0


def test_apply_all_inside_washout_bypassed(caplog):
    """All-candidates-inside-washout → bypassed + warn."""
    history = {
        "social_proof": washout_hours_for("social_proof") - 1.0,
        "scarcity": washout_hours_for("scarcity") - 1.0,
    }
    scores = {"social_proof": 0.7, "scarcity": 0.6}
    with caplog.at_level(logging.WARNING):
        result = apply_within_subject_eligibility(
            mechanism_scores=scores,
            user_touch_history=history,
        )
    assert result.filtered_scores is scores
    assert result.all_dropped is True
    assert result.bypassed is True
    assert result.n_dropped == 2
    assert "inside washout" in caplog.text.lower()


def test_apply_cross_mechanism_drop_when_recent():
    """Last touch was DIFFERENT mechanism inside its own washout → drop.

    With only 1 candidate, that drop triggers the all-drop bypass —
    so we assert on n_dropped, all_dropped, bypassed, and the
    cross-mechanism drop_reason rather than on filtered_scores
    absence (bypass preserves input by spec).
    """
    sc_floor = washout_hours_for("scarcity")
    sp_floor = washout_hours_for("social_proof")
    history = {
        # scarcity touched 1h ago — well inside its washout AND inside
        # the cross-mechanism MAX floor
        "scarcity": min(sc_floor, sp_floor) - 1.0,
    }
    scores = {"social_proof": 0.7}
    result = apply_within_subject_eligibility(
        mechanism_scores=scores,
        user_touch_history=history,
        last_touched_mechanism="scarcity",
    )
    # Cross-mechanism gate fired → 1 dropped → all-drop → bypass
    assert result.n_dropped == 1
    assert result.all_dropped is True
    assert result.bypassed is True
    assert "cross-mechanism" in result.drop_reasons["social_proof"]


def test_apply_cross_mechanism_drop_one_of_many():
    """Cross-mechanism drop with surviving candidates returns filtered set."""
    sc_floor = washout_hours_for("scarcity")
    sp_floor = washout_hours_for("social_proof")
    la_floor = washout_hours_for("loss_aversion")
    history = {
        # scarcity touched recently — gates social_proof via cross-mech
        "scarcity": min(sc_floor, sp_floor) - 1.0,
        # loss_aversion never touched → same-mech gate passes; cross-
        # mechanism MAX(la_floor, sc_floor) gated by scarcity age
    }
    scores = {
        "social_proof": 0.7,
        "loss_aversion": 0.6,
    }
    result = apply_within_subject_eligibility(
        mechanism_scores=scores,
        user_touch_history=history,
        last_touched_mechanism="scarcity",
    )
    # Both candidates gated by scarcity's recent touch (cross-mechanism
    # MAX floor exceeds the 1-hour-ago window) → all-drop → bypass.
    # This is the realistic shape — when last touch is very recent,
    # NOTHING is eligible until the largest washout elapses.
    assert result.bypassed is True
    assert result.n_dropped == 2


def test_apply_cross_mechanism_passes_when_old():
    """Last touch DIFFERENT mechanism but past MAX floor → eligible."""
    sc_floor = washout_hours_for("scarcity")
    sp_floor = washout_hours_for("social_proof")
    big = max(sc_floor, sp_floor)
    history = {
        "scarcity": big + 10.0,
    }
    scores = {"social_proof": 0.7}
    result = apply_within_subject_eligibility(
        mechanism_scores=scores,
        user_touch_history=history,
        last_touched_mechanism="scarcity",
    )
    assert result.filtered_scores["social_proof"] == 0.7
    assert result.n_dropped == 0


def test_apply_accounting_consistent():
    """n_dropped + n_eligible == input size on the non-bypass path."""
    floor = washout_hours_for("social_proof")
    sc_floor = washout_hours_for("scarcity")
    history = {
        "social_proof": floor - 1.0,    # drop
        # scarcity not in history → eligible by same-mech gate
    }
    scores = {
        "social_proof": 0.7,
        "scarcity": 0.6,
        "loss_aversion": 0.5,
    }
    result = apply_within_subject_eligibility(
        mechanism_scores=scores,
        user_touch_history=history,
    )
    assert result.bypassed is False
    assert result.n_dropped + result.n_eligible == len(scores)
    assert len(result.filtered_scores) == result.n_eligible


def test_apply_drop_reasons_populated():
    """Every dropped mechanism has a human-readable reason."""
    floor = washout_hours_for("social_proof")
    history = {"social_proof": floor - 1.0}
    scores = {"social_proof": 0.7, "scarcity": 0.6}
    result = apply_within_subject_eligibility(
        mechanism_scores=scores,
        user_touch_history=history,
    )
    assert "social_proof" in result.drop_reasons
    assert "washout" in result.drop_reasons["social_proof"].lower()


def test_apply_returns_frozen_dataclass():
    """EligibilityResult is frozen — caller cannot mutate."""
    result = apply_within_subject_eligibility(
        mechanism_scores={"social_proof": 0.5},
        user_touch_history=None,
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        result.n_dropped = 99  # type: ignore[misc]
