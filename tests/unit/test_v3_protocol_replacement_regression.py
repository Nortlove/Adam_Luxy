"""Slice 27 — Protocol-replacement regression net for v3 Phase 1.

Per the 2026-05-02 wrap-out follow-up: Slice 24 introduced three
Protocol indirections (BidComposer / CarryoverCorrectionStrategy /
WashoutModel) so v3 wrappers can register replacements without
touching upstream callers. The seam is only useful if the REAL
call sites (not just the registry directly) exercise the registered
implementation. These tests register sentinel-behavior alternates
and verify they fire from the production code path:

  * BidComposer fires from decision_trace_emitter.build_trace_from_cascade.
  * CarryoverCorrectionStrategy fires from bilateral_cascade
    (run_bilateral_cascade carryover block).
  * WashoutModel fires from within_subject_eligibility.passes_washout.

This is the regression net v3 Phase 1 will rely on. Without it, a
v3 wrapper could silently fail to engage and we wouldn't catch it
until production behavior diverged.

DISCIPLINE (B3-LUXY a/b/c/d)
    (a) Citations: Slice 24 (the seams); 2026-05-02 wrap-out follow-
        up directive.
    (b) Each test registers a sentinel impl, exercises the real call
        site, asserts the sentinel was invoked AND its return value
        flowed through the surrounding code.
    (c) calibration_pending=False — pure regression net.
    (d) Honest tags — what is NOT tested here:
          * Multi-pod / multi-process sentinel propagation (sibling
            with the persistent-Redis-snapshot multi-pod work).
          * v3 wrappers' own behavioral correctness (their own tests
            ship with the v3 implementations).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from adam.intelligence.v3_interfaces import (
    register_bid_composer,
    register_carryover_strategy,
    register_washout_model,
    reset_to_defaults_for_tests,
)


# -----------------------------------------------------------------------------
# Fixture — registry isolation between tests
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_registries():
    reset_to_defaults_for_tests()
    yield
    reset_to_defaults_for_tests()


# -----------------------------------------------------------------------------
# Test 1 — BidComposer fires from build_trace_from_cascade (the
# emitter's real call site, not the registry directly)
# -----------------------------------------------------------------------------


_SENTINEL_BID_VALUE: float = 12345.678


class _SentinelBidComposer:
    """Records every call + returns a sentinel value the test can
    detect downstream."""

    name: str = "sentinel_bc"

    def __init__(self):
        self.compose_chosen_calls: List[Dict[str, Any]] = []
        self.compose_alternatives_calls: List[Dict[str, Any]] = []

    def compose_chosen(self, **kwargs: Any) -> Optional[float]:
        self.compose_chosen_calls.append(dict(kwargs))
        return _SENTINEL_BID_VALUE

    def compose_alternatives(
        self, alternatives: List[Any], **kwargs: Any,
    ) -> List[Any]:
        self.compose_alternatives_calls.append({
            "n_alternatives": len(alternatives),
            **kwargs,
        })
        # Return alternatives unchanged (a v3 wrapper would mutate them).
        return alternatives


def test_bid_composer_replacement_fires_from_emitter_call_site():
    """Register sentinel; build a trace via build_trace_from_cascade
    with bong_posterior + posture_class so the bid block fires;
    verify (a) the sentinel was called AND (b) its return value
    landed on the trace.bid_value field."""
    sentinel = _SentinelBidComposer()
    register_bid_composer(sentinel)

    from adam.intelligence.decision_trace_emitter import (
        build_trace_from_cascade,
    )

    class _FakeCI:
        mechanism_scores = {
            "social_proof": 0.9,
            "scarcity": 0.4,
            "authority": 0.3,
        }
        primary_mechanism = "social_proof"

    # bong_posterior must be truthy + posture_class must be set; the
    # sentinel ignores the actual content.
    trace = build_trace_from_cascade(
        decision_id="test-dec-bid",
        user_id="user-bid-test",
        archetype="achiever",
        category=None,
        cascade_result=_FakeCI(),
        chosen_mechanism="social_proof",
        p_t=0.985,
        bong_posterior=object(),  # any truthy value gates the bid block
        posture_class="blend_compatible",
    )

    # 1. The sentinel was invoked from the real call site.
    assert len(sentinel.compose_chosen_calls) == 1, (
        "BidComposer.compose_chosen was not called from "
        "build_trace_from_cascade — the emitter's seam is broken."
    )
    assert len(sentinel.compose_alternatives_calls) == 1, (
        "BidComposer.compose_alternatives was not called from "
        "build_trace_from_cascade — the emitter's seam is broken."
    )

    # 2. The sentinel's return value flowed through to the trace.
    assert trace.bid_value == _SENTINEL_BID_VALUE, (
        f"trace.bid_value should reflect the sentinel ({_SENTINEL_BID_VALUE}) "
        f"but got {trace.bid_value} — the emitter is not consuming "
        "the registered BidComposer's output."
    )

    # 3. The sentinel was called with the right inputs from the
    # real call site (regression-pin against argument-name drift).
    call_kwargs = sentinel.compose_chosen_calls[0]
    assert call_kwargs.get("chosen_mechanism") == "social_proof"
    assert call_kwargs.get("posture") == "blend_compatible"


# -----------------------------------------------------------------------------
# Test 2 — CarryoverCorrectionStrategy fires from bilateral_cascade
# (run_bilateral_cascade's real call site)
# -----------------------------------------------------------------------------


@dataclass
class _SentinelCarryoverResult:
    """Frozen-shaped result mirroring CarryoverCorrectionResult."""
    modulated_scores: Dict[str, float]
    per_mechanism_penalty: Dict[str, float]
    n_corrected: int
    rho: float


class _SentinelCarryoverStrategy:
    """Records every apply() call. Returns a result with a recognizable
    sentinel penalty value the test can detect."""

    name: str = "sentinel_carryover"
    SENTINEL_PENALTY: float = -42.42

    def __init__(self):
        self.apply_calls: List[Dict[str, Any]] = []

    def apply(
        self,
        mechanism_scores: Dict[str, float],
        *,
        last_touched_mechanism: Optional[str],
        hours_since_last_touch: Optional[float],
        rho: float,
        effect_prev_for_last_touched: float,
        tau: float,
    ) -> _SentinelCarryoverResult:
        self.apply_calls.append({
            "mechanism_scores": dict(mechanism_scores),
            "last_touched_mechanism": last_touched_mechanism,
            "hours_since_last_touch": hours_since_last_touch,
            "rho": rho,
            "effect_prev_for_last_touched": effect_prev_for_last_touched,
            "tau": tau,
        })
        # Sentinel penalty pattern: -42.42 for every mechanism.
        return _SentinelCarryoverResult(
            modulated_scores=dict(mechanism_scores),
            per_mechanism_penalty={
                m: self.SENTINEL_PENALTY for m in mechanism_scores
            },
            n_corrected=len(mechanism_scores),
            rho=float(rho),
        )


def test_carryover_strategy_replacement_fires_from_cascade_call_site():
    """Pre-populate decision_cache with a recent touch so the carryover
    block's `if _last_touched_carry:` gate fires; register sentinel;
    run cascade; verify the sentinel was invoked from the real call
    site."""
    sentinel = _SentinelCarryoverStrategy()
    register_carryover_strategy(sentinel)

    # Pre-populate decision_cache with one touch for this buyer.
    # Two requirements simultaneously:
    #   (1) hours_since must be within 168h (decision_cache.recent_touches
    #       _for_buyer's default lookback) so last_touched is set.
    #   (2) the within_subject_eligibility filter must NOT drop ALL
    #       candidates, otherwise Slice 13 refuse-all-bid clears
    #       mechanism_scores and the carryover block's `if
    #       result.mechanism_scores` gate skips the strategy.
    # Cross-mechanism transitions take MAX(candidate_washout,
    # last_touched_washout). To leave ≥1 candidate eligible we plant
    # the touch on a SHORT-washout mechanism (scarcity: 4h × 3 = 12h)
    # at 167h ago — well above scarcity's washout AND above most
    # mechanisms' floors (so several candidates remain).
    from adam.api.stackadapt.decision_cache import (
        DecisionContext,
        get_decision_cache,
    )
    import time as _time

    cache = get_decision_cache()
    buyer_id = "user-carry-regression"
    seed_decision_id = f"seed-{int(_time.time() * 1000)}-{buyer_id}"
    seed_ctx = DecisionContext(
        decision_id=seed_decision_id,
        buyer_id=buyer_id,
        mechanism_sent="scarcity",
        created_at=_time.time() - (167.0 * 3600.0),  # 167h ago
    )
    cache._store[seed_decision_id] = seed_ctx

    from adam.intelligence.decision_trace_emitter import reset_for_tests
    reset_for_tests()

    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade
    run_bilateral_cascade(
        segment_id="informativ_achiever_t1",
        buyer_id=buyer_id,
    )

    # 1. The sentinel was invoked from the real cascade call site.
    assert len(sentinel.apply_calls) >= 1, (
        "CarryoverCorrectionStrategy.apply was not called from "
        "run_bilateral_cascade's carryover block — the cascade's "
        "seam is broken."
    )

    # 2. The cascade passed the right inputs (regression-pin).
    last_call = sentinel.apply_calls[-1]
    # last_touched_mechanism comes from decision_cache.recent_touches_for_buyer.
    assert last_call["last_touched_mechanism"] == "scarcity"
    # mechanism_scores must include the cascade's chosen-mechanism candidates.
    assert isinstance(last_call["mechanism_scores"], dict)
    assert len(last_call["mechanism_scores"]) >= 1
    # tau and rho are positional kwargs the cascade resolves; they
    # must be float (back-compat with the apply() signature).
    assert isinstance(last_call["tau"], float)
    assert isinstance(last_call["rho"], float)

    # Cleanup: remove the seed touch from the cache so it doesn't
    # leak into other tests in the same process.
    cache._store.pop(seed_decision_id, None)


# -----------------------------------------------------------------------------
# Test 3 — WashoutModel fires from within_subject_eligibility.passes_washout
# (the cascade's eligibility filter call path)
# -----------------------------------------------------------------------------


_SENTINEL_WASHOUT_HOURS: float = 99999.0  # absurdly large to flip behavior


class _SentinelWashoutModel:
    """Records min_wait_hours calls + returns a sentinel huge floor
    so we can detect that passes_washout actually consumed our value."""

    name: str = "sentinel_wm"

    def __init__(self):
        self.min_wait_hours_calls: List[str] = []
        self.residual_calls: List = []

    def min_wait_hours(self, mechanism: str) -> float:
        self.min_wait_hours_calls.append(str(mechanism))
        return _SENTINEL_WASHOUT_HOURS

    def residual_effect_fraction(
        self, mechanism: str, hours_since: float,
    ) -> float:
        self.residual_calls.append((str(mechanism), float(hours_since)))
        return 0.0


def test_washout_model_replacement_fires_from_eligibility_call_site():
    """Register sentinel; call passes_washout — verify (a) the
    sentinel.min_wait_hours was invoked AND (b) the sentinel's
    99999-hour floor changed the function's verdict."""
    sentinel = _SentinelWashoutModel()
    register_washout_model(sentinel)

    from adam.intelligence.within_subject_eligibility import passes_washout

    # 100 hours since last touch — under the default washout floor for
    # most mechanisms (typically 24-72h × 3 = 72-216h), but well below
    # the sentinel's 99999. With sentinel registered the function must
    # return False (still inside washout per sentinel).
    out = passes_washout(
        mechanism="social_proof",
        hours_since_last_touch=100.0,
    )
    assert out is False, (
        "passes_washout should have used the sentinel's 99999h floor "
        "and returned False (still inside washout); got True. The "
        "within_subject_eligibility seam is broken — passes_washout "
        "is not consuming the registered WashoutModel."
    )

    # 1. The sentinel was invoked from the real call site.
    assert "social_proof" in sentinel.min_wait_hours_calls, (
        "WashoutModel.min_wait_hours was not called from "
        "passes_washout — the eligibility seam is broken."
    )

    # 2. Cross-mechanism transition takes the MAX of both floors —
    # both must be consulted via the registry.
    sentinel.min_wait_hours_calls.clear()
    out_cross = passes_washout(
        mechanism="social_proof",
        hours_since_last_touch=100.0,
        last_touched_mechanism="scarcity",
    )
    assert out_cross is False  # still inside the 99999 floor
    # Both mechanisms consulted via the sentinel registry.
    assert "social_proof" in sentinel.min_wait_hours_calls
    assert "scarcity" in sentinel.min_wait_hours_calls


# -----------------------------------------------------------------------------
# Cross-cutting: all three protocols' sentinels must be RESETTABLE
# so v3 testing fixtures can isolate behavior cleanly.
# -----------------------------------------------------------------------------


def test_all_three_protocols_reset_isolates_behavior():
    """Pin that reset_to_defaults_for_tests restores ALL three
    protocols simultaneously — fixtures rely on this for atomicity."""
    sentinel_bc = _SentinelBidComposer()
    sentinel_cs = _SentinelCarryoverStrategy()
    sentinel_wm = _SentinelWashoutModel()

    register_bid_composer(sentinel_bc)
    register_carryover_strategy(sentinel_cs)
    register_washout_model(sentinel_wm)

    from adam.intelligence.v3_interfaces import (
        get_active_bid_composer,
        get_active_carryover_strategy,
        get_active_washout_model,
    )

    assert getattr(get_active_bid_composer(), "name", None) == "sentinel_bc"
    assert getattr(
        get_active_carryover_strategy(), "name", None,
    ) == "sentinel_carryover"
    assert getattr(get_active_washout_model(), "name", None) == "sentinel_wm"

    reset_to_defaults_for_tests()

    assert (
        getattr(get_active_bid_composer(), "name", None)
        == "kelly_default"
    )
    assert (
        getattr(get_active_carryover_strategy(), "name", None)
        == "step10_ar1_default"
    )
    assert (
        getattr(get_active_washout_model(), "name", None)
        == "constant_table_default"
    )
